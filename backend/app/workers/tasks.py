import asyncio
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime
from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.db import engine
from app.models.models import WebhookEventLog, WebhookStatus
from sqlmodel import select

logger = get_task_logger(__name__)

def run_async(coro):
    """Helper to run async code in sync celery worker."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

from app.models.models import (
    Message,
    DeliveryStatus,
    FlowVersion,
    ExecutionInstance,
    ExecutionStatus,
    Flow
)
from app.domain.contacts import normalize_phone
from app.domain.contacts import resolve_or_create_contact
from app.core.adk.runner import run_for_contact
from app.services.dispatch_service import DispatchService

logger = get_task_logger(__name__)

def parse_webhook_payload(provider: str, payload: Dict) -> Dict:
    """Extract normalized fields from provider payloads."""
    normalized = {
        "trigger_type": None,
        "provider_user_id": None,
        "content": None,
        "first_name": None,
        "media_id": None,
        "media_type": None,
        "mime_type": None,
        "caption": None,
        "channel": None,            # instagram | messenger | lead_ads
        "attachment_url": None,
        "leadgen_id": None,
        "meta_delivery_watermark": None,
        "meta_read_watermark": None,
    }

    try:
        if provider == "whatsapp":
            entry = payload.get("entry", [])[0]
            value = entry.get("changes", [])[0].get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            if messages:
                msg = messages[0]
                msg_type = msg.get("type", "text")
                normalized["trigger_type"] = "MESSAGE_INBOUND"
                normalized["provider_user_id"] = msg.get("from")
                if contacts:
                    normalized["first_name"] = contacts[0].get("profile", {}).get("name")

                if msg_type == "text":
                    normalized["content"] = msg.get("text", {}).get("body")
                elif msg_type in ("image", "audio", "video", "document"):
                    media_obj = msg.get(msg_type, {})
                    normalized["media_id"] = media_obj.get("id")
                    normalized["media_type"] = msg_type
                    normalized["mime_type"] = media_obj.get("mime_type")
                    normalized["caption"] = media_obj.get("caption")
                    normalized["content"] = media_obj.get("caption") or f"[{msg_type}]"

            # WhatsApp status updates (delivery receipts)
            statuses = value.get("statuses", [])
            if statuses and not messages:
                normalized["trigger_type"] = "STATUS_UPDATE"
                normalized["statuses"] = statuses

        elif provider == "meta":
            entry = payload.get("entry", [])[0]

            # Channel discrimination: instagram vs messenger
            object_type = payload.get("object", "")
            if object_type == "instagram":
                normalized["channel"] = "instagram"
            else:
                normalized["channel"] = "messenger"

            # Messaging (Messenger/Instagram)
            if "messaging" in entry:
                msg_event = entry["messaging"][0]

                # Delivery receipts (watermark-based)
                if "delivery" in msg_event:
                    normalized["trigger_type"] = "META_STATUS_UPDATE"
                    normalized["meta_delivery_watermark"] = msg_event["delivery"].get("watermark")
                elif "read" in msg_event:
                    normalized["trigger_type"] = "META_STATUS_UPDATE"
                    normalized["meta_read_watermark"] = msg_event["read"].get("watermark")
                elif msg_event.get("message"):
                    # Standard inbound message
                    normalized["trigger_type"] = "MESSAGE_INBOUND"
                    normalized["provider_user_id"] = msg_event.get("sender", {}).get("id")
                    message = msg_event.get("message", {})
                    normalized["content"] = message.get("text")

                    # Attachment parsing
                    attachments = message.get("attachments", [])
                    if attachments:
                        att = attachments[0]
                        att_type = att.get("type")
                        normalized["media_type"] = att_type
                        normalized["attachment_url"] = att.get("payload", {}).get("url")
                        if not normalized["content"]:
                            normalized["content"] = f"[{att_type}]"

            # Lead Ads
            elif "changes" in entry:
                change = entry["changes"][0]
                if change.get("field") == "leadgen":
                    normalized["trigger_type"] = "LEAD_AD_SUBMIT"
                    normalized["leadgen_id"] = change.get("value", {}).get("leadgen_id")
                    normalized["provider_user_id"] = normalized["leadgen_id"]
                    normalized["channel"] = "lead_ads"
                    normalized["content"] = "Lead Ad Submission"
    except (IndexError, KeyError, AttributeError):
        pass

    return normalized


# Status priority for forward-only progression
_STATUS_PRIORITY = {
    DeliveryStatus.PENDING: 0,
    DeliveryStatus.SENDING: 1,
    DeliveryStatus.SENT: 2,
    DeliveryStatus.DELIVERED: 3,
    DeliveryStatus.READ: 4,
    DeliveryStatus.FAILED: 5,
    DeliveryStatus.DEAD_LETTER: 6,
}


async def _process_status_updates(session, statuses: list, workspace_id, correlation_id: str):
    """Process WhatsApp delivery status webhooks (sent/delivered/read/failed)."""
    from app.services.runtime_event_service import log_event

    status_map = {
        "sent": DeliveryStatus.SENT,
        "delivered": DeliveryStatus.DELIVERED,
        "read": DeliveryStatus.READ,
        "failed": DeliveryStatus.FAILED,
    }

    for s in statuses:
        provider_msg_id = s.get("id")
        wa_status = s.get("status")
        timestamp_str = s.get("timestamp")

        if not provider_msg_id or wa_status not in status_map:
            continue

        result = await session.execute(
            select(Message).where(Message.provider_message_id == provider_msg_id)
        )
        msg = result.scalars().first()
        if not msg:
            logger.info(f"Status update for unknown message {provider_msg_id}, skipping")
            continue

        new_status = status_map[wa_status]
        old_priority = _STATUS_PRIORITY.get(msg.delivery_status, 0)
        new_priority = _STATUS_PRIORITY.get(new_status, 0)

        # Only advance forward (don't regress from READ → DELIVERED)
        if new_priority <= old_priority:
            continue

        ts = datetime.utcfromtimestamp(int(timestamp_str)) if timestamp_str else datetime.utcnow()

        msg.delivery_status = new_status
        if new_status == DeliveryStatus.SENT and not msg.sent_at:
            msg.sent_at = ts
        elif new_status == DeliveryStatus.DELIVERED:
            msg.delivered_at = ts
        elif new_status == DeliveryStatus.READ:
            msg.read_at = ts
        elif new_status == DeliveryStatus.FAILED:
            errors = s.get("errors", [])
            msg.failure_code = str(errors[0].get("code")) if errors else None
            msg.last_error = errors[0].get("title") if errors else "Unknown failure"

        session.add(msg)
        await log_event(session, event_type="message.status_updated", source="webhook",
                        workspace_id=workspace_id, correlation_id=correlation_id,
                        related_ids={"message_id": str(msg.id)},
                        payload={"status": wa_status, "provider_message_id": provider_msg_id})


async def _process_meta_status_updates(session, info: dict, workspace_id, correlation_id: str):
    """Process Meta delivery/read status webhooks using watermark timestamps."""
    from app.services.runtime_event_service import log_event
    from sqlmodel import or_

    delivery_watermark = info.get("meta_delivery_watermark")
    read_watermark = info.get("meta_read_watermark")

    if delivery_watermark:
        watermark_ts = datetime.utcfromtimestamp(int(delivery_watermark) / 1000)
        result = await session.execute(
            select(Message).where(
                Message.workspace_id == workspace_id,
                Message.platform == "meta",
                Message.direction == "outbound",
                Message.delivery_status == DeliveryStatus.SENT,
                Message.sent_at < watermark_ts,
            )
        )
        for msg in result.scalars().all():
            old_priority = _STATUS_PRIORITY.get(msg.delivery_status, 0)
            new_priority = _STATUS_PRIORITY.get(DeliveryStatus.DELIVERED, 0)
            if new_priority > old_priority:
                msg.delivery_status = DeliveryStatus.DELIVERED
                msg.delivered_at = watermark_ts
                session.add(msg)

    if read_watermark:
        watermark_ts = datetime.utcfromtimestamp(int(read_watermark) / 1000)
        result = await session.execute(
            select(Message).where(
                Message.workspace_id == workspace_id,
                Message.platform == "meta",
                Message.direction == "outbound",
                or_(
                    Message.delivery_status == DeliveryStatus.SENT,
                    Message.delivery_status == DeliveryStatus.DELIVERED,
                ),
                Message.sent_at < watermark_ts,
            )
        )
        for msg in result.scalars().all():
            old_priority = _STATUS_PRIORITY.get(msg.delivery_status, 0)
            new_priority = _STATUS_PRIORITY.get(DeliveryStatus.READ, 0)
            if new_priority > old_priority:
                msg.delivery_status = DeliveryStatus.READ
                msg.read_at = watermark_ts
                if not msg.delivered_at:
                    msg.delivered_at = watermark_ts
                session.add(msg)

    await log_event(session, event_type="message.meta_status_updated", source="webhook",
                    workspace_id=workspace_id, correlation_id=correlation_id,
                    payload={"delivery_watermark": delivery_watermark,
                             "read_watermark": read_watermark})


@celery_app.task(name="app.workers.tasks.process_webhook_event")
def process_webhook_event(event_id: str):
    """
    Process a stored webhook event and trigger automation flows.
    """
    async def _run():
        logger.info(f"Processing webhook event: {event_id}")
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.services.runtime_event_service import log_event

        async with AsyncSession(engine, expire_on_commit=False) as session:
            event = await session.get(WebhookEventLog, UUID(event_id))
            if not event or not event.workspace_id:
                logger.error(f"Event {event_id} not found or has no workspace")
                return

            event.status = WebhookStatus.QUEUED
            session.add(event)
            await log_event(session, event_type="webhook.processing_started", source="webhook",
                            workspace_id=event.workspace_id, correlation_id=str(event.correlation_id),
                            related_ids={"webhook_event_id": event_id})
            await session.commit()

            try:
                # 0. Loop Prevention (Part D)
                is_echo = False
                if event.provider == "meta":
                    entry = event.payload.get("entry", [{}])[0]
                    if "messaging" in entry:
                        msg_event = entry["messaging"][0]
                        if msg_event.get("message", {}).get("is_echo"):
                            is_echo = True

                if is_echo:
                    logger.info(f"Ignoring echo event {event_id} to prevent loops")
                    event.status = WebhookStatus.PROCESSED
                    session.add(event)
                    await session.commit()
                    return

                # 1. Parse Payload
                info = parse_webhook_payload(event.provider, event.payload)

                # 1a. Handle WhatsApp delivery status updates
                if info.get("trigger_type") == "STATUS_UPDATE" and info.get("statuses"):
                    await _process_status_updates(
                        session, info["statuses"], event.workspace_id,
                        str(event.correlation_id)
                    )
                    event.status = WebhookStatus.PROCESSED
                    event.processed_at = datetime.utcnow()
                    session.add(event)
                    await session.commit()
                    return

                # 1a2. Handle Meta delivery/read status updates (watermark-based)
                if info.get("trigger_type") == "META_STATUS_UPDATE":
                    await _process_meta_status_updates(
                        session, info, event.workspace_id,
                        str(event.correlation_id)
                    )
                    event.status = WebhookStatus.PROCESSED
                    event.processed_at = datetime.utcnow()
                    session.add(event)
                    await session.commit()
                    return

                if not info["trigger_type"]:
                    logger.info(f"No actionable trigger found in payload for event {event_id}")
                    event.status = WebhookStatus.PROCESSED
                    session.add(event)
                    await session.commit()
                    return

                # 1b. Normalize phone number for WhatsApp
                if event.provider == "whatsapp" and info.get("provider_user_id"):
                    info["provider_user_id"] = normalize_phone(info["provider_user_id"])

                # 2. Resolve Contact & Store Message
                contact, identity, conversation = await resolve_or_create_contact(
                    session,
                    event.workspace_id,
                    event.provider,
                    info["provider_user_id"],
                    first_name=info["first_name"]
                )

                if info["trigger_type"] == "MESSAGE_INBOUND":
                    msg_metadata = {}
                    if info.get("channel"):
                        msg_metadata["channel"] = info["channel"]
                    if info.get("attachment_url"):
                        msg_metadata["attachment_url"] = info["attachment_url"]
                        msg_metadata["media_type"] = info.get("media_type")
                    if info.get("media_id"):
                        msg_metadata["media_id"] = info["media_id"]
                        msg_metadata["media_type"] = info["media_type"]
                        msg_metadata["mime_type"] = info["mime_type"]
                        # Download and store media (WhatsApp)
                        try:
                            from app.services.media_service import download_and_store_media
                            media_path = await download_and_store_media(
                                session, event.workspace_id, info["media_id"],
                                info["mime_type"], event.provider
                            )
                            if media_path:
                                msg_metadata["media_path"] = media_path
                        except Exception as media_err:
                            logger.warning(f"Media download failed for {info['media_id']}: {media_err}")

                    inbound_msg = Message(
                        workspace_id=event.workspace_id,
                        conversation_id=conversation.id,
                        direction="inbound",
                        content=info["content"] or "",
                        platform=event.provider,
                        delivery_status="delivered",
                        additional_metadata=msg_metadata,
                    )
                    session.add(inbound_msg)

                # 2b. Lead Ads: fetch lead data and enrich contact
                if info["trigger_type"] == "LEAD_AD_SUBMIT" and info.get("leadgen_id"):
                    from app.services.meta_service import fetch_lead_data, parse_lead_fields
                    from app.models.models import Integration
                    from app.core.security import decrypt_data
                    from app.services.metrics_service import metrics

                    integration_result = await session.execute(
                        select(Integration).where(
                            Integration.workspace_id == event.workspace_id,
                            Integration.provider == "meta"
                        )
                    )
                    integration = integration_result.scalars().first()
                    if integration and integration.encrypted_config:
                        try:
                            config = decrypt_data(integration.encrypted_config)
                            lead_raw = await fetch_lead_data(
                                info["leadgen_id"], config.get("access_token")
                            )
                            lead_fields = parse_lead_fields(
                                lead_raw.get("field_data", [])
                            )

                            # Enrich contact metadata
                            updated_meta = dict(contact.additional_metadata or {})
                            if lead_fields.get("email"):
                                updated_meta["email"] = lead_fields["email"]
                            if lead_fields.get("phone"):
                                updated_meta["phone"] = lead_fields["phone"]
                            updated_meta["lead_source"] = "meta_lead_ad"
                            updated_meta["leadgen_id"] = info["leadgen_id"]
                            contact.additional_metadata = updated_meta

                            if lead_fields.get("first_name") and not contact.first_name:
                                contact.first_name = lead_fields["first_name"]
                            if lead_fields.get("last_name") and not contact.last_name:
                                contact.last_name = lead_fields["last_name"]
                            session.add(contact)

                            # Store lead as message
                            lead_msg = Message(
                                workspace_id=event.workspace_id,
                                conversation_id=conversation.id,
                                direction="inbound",
                                content=f"Lead Ad: {lead_fields.get('full_name', lead_fields.get('first_name', 'Unknown'))}",
                                platform="meta",
                                delivery_status="delivered",
                                additional_metadata={
                                    "type": "lead_ad_submission",
                                    "leadgen_id": info["leadgen_id"],
                                    "lead_fields": lead_fields,
                                    "channel": "lead_ads",
                                },
                            )
                            session.add(lead_msg)
                            metrics.increment("meta_leads_ingested")
                            await log_event(
                                session, event_type="meta.lead_ingested",
                                source="webhook",
                                workspace_id=event.workspace_id,
                                correlation_id=str(event.correlation_id),
                                payload={"leadgen_id": info["leadgen_id"]},
                            )
                        except Exception as lead_err:
                            logger.warning(f"Lead data fetch failed for {info['leadgen_id']}: {lead_err}")

                # 3. Find Matching Published Flow (prefer published_version_id pointer)
                flow_version = None
                flow_query = select(Flow).where(
                    Flow.workspace_id == event.workspace_id,
                    Flow.status == "published",
                    Flow.published_version_id != None,  # noqa: E711
                ).limit(1)
                flow_result = (await session.execute(flow_query)).scalars().first()
                if flow_result and flow_result.published_version_id:
                    flow_version = await session.get(FlowVersion, flow_result.published_version_id)

                # Fallback: legacy flows published before Mission 27 (published_version_id not set)
                if not flow_version:
                    legacy_query = select(FlowVersion).join(Flow).where(
                        Flow.workspace_id == event.workspace_id,
                        FlowVersion.is_published == True
                    ).order_by(FlowVersion.created_at.desc())
                    flow_version = (await session.execute(legacy_query)).scalars().first()

                if flow_version:
                    # 4. Create Execution Instance
                    nodes = flow_version.definition_json.get("nodes", [])
                    # Use start_node_id if available (Mission 27 format), else find TRIGGER node
                    start_node_id = flow_version.definition_json.get("start_node_id")
                    if start_node_id:
                        start_node = next((n for n in nodes if n.get("id") == start_node_id), None)
                    else:
                        start_node = next((n for n in nodes if n.get("type") == "TRIGGER"), None)
                    if not start_node and nodes:
                        start_node = nodes[0]

                    instance = ExecutionInstance(
                        workspace_id=event.workspace_id,
                        flow_version_id=flow_version.id,
                        contact_id=contact.id,
                        status=ExecutionStatus.RUNNING,
                        current_node_id=UUID(start_node["id"]) if start_node else None
                    )
                    session.add(instance)
                    await log_event(session, event_type="runtime.execution_created", source="runtime",
                                    workspace_id=event.workspace_id, correlation_id=str(event.correlation_id),
                                    related_ids={"webhook_event_id": event_id, "execution_instance_id": str(instance.id)})
                    await session.commit()

                    # 5. Execute Runtime (ADK — Mission M-A)
                    await run_for_contact(
                        workspace_id=event.workspace_id,
                        contact_id=contact.id,
                        conversation_id=conversation.id,
                        inbound_message=info.get("content") or "",
                        execution_instance=instance,
                        session=session,
                    )

                # Mark event success
                event.status = WebhookStatus.PROCESSED
                event.processed_at = datetime.utcnow()
                session.add(event)
                await log_event(session, event_type="webhook.processing_completed", source="webhook",
                                workspace_id=event.workspace_id, correlation_id=str(event.correlation_id),
                                related_ids={"webhook_event_id": event_id})
                await session.commit()

            except Exception as e:
                logger.exception(f"Failed to process event {event_id}")
                event.status = WebhookStatus.FAILED
                event.last_error = str(e)
                event.attempts += 1
                session.add(event)
                await log_event(session, event_type="webhook.processing_failed", source="webhook",
                                workspace_id=event.workspace_id, correlation_id=str(event.correlation_id),
                                outcome="failure", error_message=str(e),
                                related_ids={"webhook_event_id": event_id})
                await session.commit()

    run_async(_run())

@celery_app.task(name="app.workers.tasks.dispatch_message_task")
def dispatch_message_task(message_id: str):
    """Immediate dispatch task for a single outbound message."""
    logger.info(f"Celery: Dispatching message {message_id}")
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _run():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            msg = await session.get(Message, UUID(message_id))
            if msg:
                await DispatchService.dispatch_message(session, msg)
            else:
                logger.error(f"Message {message_id} not found for dispatch")
                
    run_async(_run())

@celery_app.task(name="app.workers.tasks.dispatch_pending_task")
def dispatch_pending_task(workspace_id: Optional[str] = None):
    """Periodic task to poll and dispatch missed outbound intents."""
    logger.info(f"Celery: Polling pending messages (Workspace: {workspace_id})")
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _run():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await DispatchService.dispatch_pending_messages(
                session,
                workspace_id=UUID(workspace_id) if workspace_id else None
            )

    run_async(_run())


async def _expire_plan_overrides_core(db):
    """Core expiry logic — accepts a session for testability."""
    from app.models.models import PlanOverride
    from app.services.audit_service import audit_event

    now = datetime.utcnow()
    result = await db.execute(
        select(PlanOverride).where(
            PlanOverride.status == "active",
            PlanOverride.ends_at <= now,
        )
    )
    stale = result.scalars().all()
    for override in stale:
        override.status = "expired"
        await audit_event(
            db=db,
            action="PLAN_OVERRIDE_EXPIRED",
            entity_type="plan_override",
            entity_id=str(override.id),
            actor_type="system",
            workspace_id=override.workspace_id,
            outcome="success",
            metadata={"ends_at": override.ends_at.isoformat()},
        )
    if stale:
        await db.commit()
        logger.info(f"[expire_plan_overrides_task] Expired {len(stale)} plan override(s)")


@celery_app.task(name="app.workers.tasks.expire_plan_overrides_task")
def expire_plan_overrides_task():
    """Every-5-min task: mark ACTIVE plan overrides past their ends_at as EXPIRED and write audit log."""
    from sqlalchemy.ext.asyncio import AsyncSession

    async def _run():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await _expire_plan_overrides_core(session)

    run_async(_run())


@celery_app.task(name="app.workers.tasks.purge_runtime_events_task")
def purge_runtime_events_task():
    """Daily task to purge old runtime events based on retention policy."""
    from app.core.config import settings as app_settings
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.models import RuntimeEventLog
    from datetime import timedelta
    from sqlalchemy import delete as sa_delete

    async def _run():
        cutoff = datetime.utcnow() - timedelta(days=app_settings.RUNTIME_EVENT_RETENTION_DAYS)
        total_purged = 0
        async with AsyncSession(engine, expire_on_commit=False) as session:
            while True:
                query = select(RuntimeEventLog.id).where(
                    RuntimeEventLog.created_at < cutoff
                ).limit(1000)
                result = await session.execute(query)
                ids = [row[0] for row in result.all()]
                if not ids:
                    break
                await session.execute(
                    sa_delete(RuntimeEventLog).where(RuntimeEventLog.id.in_(ids))
                )
                await session.commit()
                total_purged += len(ids)
        logger.info(f"Purged {total_purged} runtime events older than {app_settings.RUNTIME_EVENT_RETENTION_DAYS} days")

    run_async(_run())


@celery_app.task(name="app.workers.tasks.export_to_hf_task")
def export_to_hf_task():
    """Daily task: export all LeadPilot data (static + dynamic) to HuggingFace dataset repo.
    Silently no-ops if HF_TOKEN or HF_DATASET_REPO is not configured."""
    import sys as _sys
    import os as _os
    from app.core.config import settings as app_settings

    if not app_settings.HF_TOKEN or not app_settings.HF_DATASET_REPO:
        logger.warning(
            "[export_to_hf_task] HF_TOKEN or HF_DATASET_REPO not configured — skipping export."
        )
        return

    async def _run():
        # Locate scripts/ directory relative to this file: app/workers/tasks.py → backend/scripts/
        scripts_dir = _os.path.join(
            _os.path.dirname(  # backend/
                _os.path.dirname(  # app/
                    _os.path.dirname(_os.path.abspath(__file__))  # app/workers/
                )
            ),
            "scripts",
        )
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        from export_to_hf import run_export

        try:
            await run_export(
                mode="all",
                batch_size=5000,
                dry_run=False,
                hf_token=app_settings.HF_TOKEN,
                repo_id=app_settings.HF_DATASET_REPO,
            )
            logger.info("[export_to_hf_task] Export completed successfully.")
        except Exception:
            logger.exception(
                "[export_to_hf_task] Export failed — will retry on next scheduled run."
            )

    run_async(_run())


@celery_app.task(name="app.workers.tasks.resume_waiting_instances_task")
def resume_waiting_instances_task():
    """
    Every-minute task: find WAITING ExecutionInstances whose delay has elapsed
    and re-trigger the ADK runner for them (Mission M-D: WAIT_DELAY support).
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.models import Conversation

    async def _run():
        now = datetime.utcnow()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(
                select(ExecutionInstance).where(
                    ExecutionInstance.status == ExecutionStatus.WAITING,
                    ExecutionInstance.resume_at <= now,
                )
            )
            instances = result.scalars().all()
            if not instances:
                return

            for instance in instances:
                try:
                    instance.status = ExecutionStatus.RUNNING
                    session.add(instance)
                    await session.flush()

                    # Resolve conversation_id for this contact in this workspace
                    conv_result = await session.execute(
                        select(Conversation).where(
                            Conversation.workspace_id == instance.workspace_id,
                            Conversation.contact_id == instance.contact_id,
                        ).limit(1)
                    )
                    conversation = conv_result.scalars().first()
                    if not conversation:
                        logger.warning(
                            f"[resume_waiting_instances_task] No conversation for instance {instance.id}"
                        )
                        continue

                    await run_for_contact(
                        workspace_id=instance.workspace_id,
                        contact_id=instance.contact_id,
                        conversation_id=conversation.id,
                        inbound_message="[Resumed after delay]",
                        execution_instance=instance,
                        session=session,
                    )
                except Exception:
                    logger.exception(
                        f"[resume_waiting_instances_task] Failed to resume instance {instance.id}"
                    )

            await session.commit()
            logger.info(f"[resume_waiting_instances_task] Resumed {len(instances)} waiting instance(s)")

    run_async(_run())
