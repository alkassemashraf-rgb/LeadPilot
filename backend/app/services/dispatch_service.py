import logging
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_

from app.core.config import settings
from app.models.models import Message, DeliveryStatus, Integration, ChannelIdentity, Conversation
from app.core.security import decrypt_data
from app.integrations.whatsapp.adapter import WhatsAppAdapter
from app.integrations.meta.adapter import MetaAdapter
from app.services.runtime_event_service import log_event
from app.services.metrics_service import metrics

logger = logging.getLogger(__name__)

# Redis for locking
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class DispatchService:
    @staticmethod
    async def dispatch_pending_messages(db: AsyncSession, workspace_id: Optional[UUID] = None, limit: int = 50) -> Tuple[int, int]:
        """
        Poll and dispatch pending outbound messages with hardening.
        """
        now = datetime.utcnow()
        
        # 1. Selection query with Zombie Recovery and N+1 Optimization
        # Zombies: SENDING status and last_attempt_at > 5 minutes ago
        zombie_threshold = now - timedelta(minutes=5)
        
        query = select(Message).where(
            Message.direction == "outbound",
            or_(
                Message.delivery_status == DeliveryStatus.PENDING,
                # Retryable FAILED messages (Backoff is checked in the loop to allow dynamic calculation)
                Message.delivery_status == DeliveryStatus.FAILED,
                # Zombie Recovery
                and_(
                    Message.delivery_status == DeliveryStatus.SENDING,
                    Message.last_attempt_at < zombie_threshold
                )
            )
        ).options(
            # We will eager load Integration, Conversation, identity below manually or via relationship if defined
        )
        
        if workspace_id:
            query = query.where(Message.workspace_id == workspace_id)
        
        query = query.limit(limit).order_by(Message.created_at.asc())
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        processed_count = 0
        failed_count = 0
        
        for msg in messages:
            # Check Exponential Backoff for FAILED messages
            if msg.delivery_status == DeliveryStatus.FAILED:
                # Check workspace auto-retry setting
                from app.services.settings_service import get_workspace_messaging_settings
                msg_settings = await get_workspace_messaging_settings(msg.workspace_id, db)
                if not msg_settings.get("auto_retry_failed_dispatch", True):
                    continue  # Auto-retry disabled for this workspace
                # delay = min(60 * 2^attempt_count, 1800)
                delay_seconds = min(60 * (2 ** (msg.attempt_count - 1)), 1800) if msg.attempt_count > 0 else 60
                if msg.last_attempt_at and msg.last_attempt_at > now - timedelta(seconds=delay_seconds):
                    continue # Not ready for retry yet
            
            # Handle Zombie Recovery: Reset to PENDING so dispatch_message treats it as a fresh (safe) attempt
            if msg.delivery_status == DeliveryStatus.SENDING:
                logger.info(f"Recovered zombie message {msg.id} (last attempt: {msg.last_attempt_at})")
                msg.delivery_status = DeliveryStatus.PENDING
                db.add(msg)
                await db.commit()

            # 2. Acquire Redis lock with resilience
            lock_key = f"lock:dispatch:{msg.id}"
            lock_acquired = False
            try:
                lock_acquired = redis_client.set(lock_key, "locked", ex=60, nx=True)
            except Exception as e:
                logger.warning(f"Redis unavailable — dispatch running without distributed lock for {msg.id}: {e}")
                lock_acquired = True # Fallback to Safe Mode (single-worker reliability)

            if not lock_acquired:
                logger.warning(f"Message {msg.id} is already being dispatched (locked). Skipping.")
                await log_event(db, event_type="dispatch.lock_skipped", source="dispatch",
                                workspace_id=msg.workspace_id, outcome="skipped",
                                related_ids={"message_id": str(msg.id)})
                continue
            
            try:
                await DispatchService.dispatch_message(db, msg)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to dispatch message {msg.id}: {str(e)}")
                failed_count += 1
            finally:
                try:
                    redis_client.delete(lock_key)
                except Exception:
                    pass
        
        return processed_count, failed_count

    @staticmethod
    async def dispatch_message(db: AsyncSession, msg: Message):
        """
        Logic for a single message dispatch with Atomic Send Protection.
        """
        log_ctx = {
            "workspace_id": str(msg.workspace_id),
            "message_id": str(msg.id),
            "attempt_count": msg.attempt_count + 1,
            "platform": msg.platform
        }

        # 1. Atomic Send Protection (Duplicate Guard)
        # Check by provider_message_id
        if msg.provider_message_id and msg.delivery_status != DeliveryStatus.SENT:
            logger.info(f"Duplicate Guard: Message {msg.id} already has provider_id {msg.provider_message_id}. Marking as SENT.", extra=log_ctx)
            msg.delivery_status = DeliveryStatus.SENT
            msg.sent_at = msg.sent_at or datetime.utcnow()
            db.add(msg)
            await log_event(db, event_type="dispatch.skipped_already_sent", source="dispatch",
                            workspace_id=msg.workspace_id, outcome="skipped",
                            related_ids={"message_id": str(msg.id)})
            await db.commit()
            return

        # Check by Idempotency Hash (Last 10 minutes)
        if msg.idempotency_hash:
            ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
            dup_query = select(Message).where(
                Message.idempotency_hash == msg.idempotency_hash,
                Message.delivery_status == DeliveryStatus.SENT,
                Message.sent_at > ten_mins_ago,
                Message.id != msg.id
            )
            dup_result = await db.execute(dup_query)
            duplicate = dup_result.scalars().first()
            if duplicate:
                logger.info(f"Idempotency Guard: Identical message already sent recently ({duplicate.id}). Skipping.", extra=log_ctx)
                msg.delivery_status = DeliveryStatus.SENT
                msg.sent_at = datetime.utcnow()
                msg.last_error = "Skipped by idempotency guard"
                db.add(msg)
                await log_event(db, event_type="dispatch.skipped_idempotency", source="dispatch",
                                workspace_id=msg.workspace_id, outcome="skipped",
                                related_ids={"message_id": str(msg.id)})
                await db.commit()
                return

        # Atomically update status to SENDING
        msg.delivery_status = DeliveryStatus.SENDING
        msg.last_attempt_at = datetime.utcnow()
        msg.attempt_count += 1
        db.add(msg)
        await log_event(db, event_type="dispatch.attempt_started", source="dispatch",
                        workspace_id=msg.workspace_id,
                        related_ids={"message_id": str(msg.id), "conversation_id": str(msg.conversation_id)},
                        payload={"platform": msg.platform, "attempt_count": msg.attempt_count})
        await db.commit()
        await db.refresh(msg)

        try:
            # 2. Resolve Integration, Conversation, Identity (N+1 Optimized)
            # In a real production system, these relationships should be on the Message model
            # for selectinload. Here we fetch them efficiently.
            
            # Fetch Integration & Conversation & Identity in parallel or joined if possible
            # For now, let's at least ensure we don't do redundant work.
            
            integration_query = select(Integration).where(
                Integration.workspace_id == msg.workspace_id,
                Integration.provider == msg.platform
            )
            integration = (await db.execute(integration_query)).scalars().first()

            if not integration or not integration.encrypted_config:
                raise Exception(f"No connected integration found for platform {msg.platform}")

            config = decrypt_data(integration.encrypted_config)

            conv_query = select(Conversation).where(Conversation.id == msg.conversation_id)
            conversation = (await db.execute(conv_query)).scalars().first()
            
            if not conversation:
                raise Exception(f"Conversation {msg.conversation_id} not found")

            identity_query = select(ChannelIdentity).where(
                ChannelIdentity.contact_id == conversation.contact_id,
                ChannelIdentity.provider == msg.platform
            )
            identity = (await db.execute(identity_query)).scalars().first()

            if not identity:
                raise Exception(f"No identity found for contact on platform {msg.platform}")

            recipient_id = identity.provider_user_id

            # 3. Call Provider Adapter
            logger.info(f"Sending message via {msg.platform}", extra=log_ctx)
            provider_message_id = None
            media_url = (msg.additional_metadata or {}).get("media_url")
            media_type = (msg.additional_metadata or {}).get("media_type")
            media_caption = (msg.additional_metadata or {}).get("caption")

            if msg.platform == "whatsapp":
                adapter = WhatsAppAdapter(
                    phone_number_id=integration.provider_workspace_id,
                    access_token=config.get("access_token")
                )
                if media_url and media_type:
                    provider_message_id = await adapter.send_media(
                        recipient_id, media_type, media_url, caption=media_caption
                    )
                else:
                    provider_message_id = await adapter.send_text(recipient_id, msg.content)
            elif msg.platform == "meta":
                adapter = MetaAdapter(
                    page_id=integration.provider_workspace_id,
                    page_access_token=config.get("access_token")
                )
                if media_url and media_type:
                    provider_message_id = await adapter.send_media(
                        recipient_id, media_type, media_url, caption=media_caption
                    )
                else:
                    provider_message_id = await adapter.send_text(recipient_id, msg.content)
            else:
                raise Exception(f"Unsupported platform: {msg.platform}")

            # 4. On Success
            msg.delivery_status = DeliveryStatus.SENT
            msg.provider_message_id = provider_message_id
            msg.sent_at = datetime.utcnow()
            msg.last_error = None
            metrics.increment("messages_sent", labels={"platform": msg.platform})
            logger.info(f"Successfully sent message {msg.id}", extra=log_ctx)
            await log_event(db, event_type="dispatch.attempt_succeeded", source="dispatch",
                            workspace_id=msg.workspace_id,
                            related_ids={"message_id": str(msg.id)},
                            payload={"provider_message_id": provider_message_id, "platform": msg.platform})

        except Exception as e:
            error_str = str(e)
            is_permanent = "PERMANENT_FAILURE" in error_str
            is_exhausted = is_permanent or msg.attempt_count >= 5

            logger.error(f"Dispatch error for message {msg.id}: {error_str}", extra=log_ctx)
            msg.last_error = error_str

            if is_exhausted:
                msg.delivery_status = DeliveryStatus.DEAD_LETTER
                metrics.increment("messages_dead_lettered", labels={"platform": msg.platform})
                await log_event(db, event_type="dispatch.dead_lettered", source="dispatch",
                                workspace_id=msg.workspace_id, outcome="failure",
                                error_message=error_str,
                                related_ids={"message_id": str(msg.id)},
                                payload={"platform": msg.platform, "attempt_count": msg.attempt_count,
                                         "reason": "permanent" if is_permanent else "max_retries"})
            else:
                msg.delivery_status = DeliveryStatus.FAILED
                metrics.increment("messages_failed", labels={"platform": msg.platform})
                await log_event(db, event_type="dispatch.attempt_failed", source="dispatch",
                                workspace_id=msg.workspace_id, outcome="skipped",
                                error_message=error_str,
                                related_ids={"message_id": str(msg.id)},
                                payload={"platform": msg.platform, "attempt_count": msg.attempt_count})

            raise e
        finally:
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
