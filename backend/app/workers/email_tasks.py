import logging
import asyncio
import json
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.celery_app import celery_app
from app.services.email_service import EmailService
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import EmailLog, EmailStatus, SystemModuleConfig, EmailOutbox, EmailOutboxStatus
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_
import hashlib

logger = logging.getLogger(__name__)

def async_to_sync(awaitable):
    """Helper to run async code in sync celery worker."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(awaitable)

async def _update_email_log(email_log_id: str, status: EmailStatus, error_message: str = None, attempt: int = None):
    async with SessionLocal() as db:
        import uuid
        log = await db.get(EmailLog, uuid.UUID(email_log_id) if isinstance(email_log_id, str) else email_log_id)
        if log:
            log.status = status
            if error_message: log.error_message = error_message
            if attempt is not None: log.attempt_count = attempt
            await db.commit()

async def _check_module_enabled(module_name: str) -> bool:
    async with SessionLocal() as db:
        result = await db.execute(select(SystemModuleConfig).where(SystemModuleConfig.module_name == module_name))
        mod = result.scalars().first()
        return mod.is_enabled if mod else True

@celery_app.task(
    name="app.workers.email_tasks.send_email_task",
    bind=True,
    max_retries=settings.EMAIL_MAX_RETRIES,
    default_retry_delay=settings.EMAIL_RETRY_BASE_DELAY
)
def send_email_task(self, email_type: str, payload: Dict[str, Any]):
    """
    Sends an email securely using the configured provider via celery worker.
    """
    to_email = payload.get("to_email")
    email_log_id = payload.get("email_log_id")
    
    if not to_email:
        logger.error("No recipient email provided in payload")
        return
        
    logger.info(f"Preparing to send {email_type} email to {to_email}")
    
    # Check module toggle
    is_enabled = async_to_sync(_check_module_enabled("email_engine"))
    if not is_enabled:
        logger.info("Module 'email_engine' is disabled. Skipping dispatch.")
        if email_log_id:
            async_to_sync(_update_email_log(email_log_id, EmailStatus.FAILED, "Module email_engine is disabled. Skipped dispatch."))
        log_entry = {
            "event": "module_disabled",
            "email_dispatch_event": "email_dispatch",
            "email_log_id": email_log_id,
            "status": "SKIPPED",
            "attempt": self.request.retries + 1
        }
        logger.info(json.dumps(log_entry))
        return
        
    success = False

    try:
        if email_type == "password_reset":
            token = payload.get("token")
            success = async_to_sync(EmailService.send_password_reset_email(to_email, token))
        elif email_type == "workspace_invite":
            token = payload.get("token")
            workspace_name = payload.get("workspace_name")
            inviter_name = payload.get("inviter_name")
            success = async_to_sync(EmailService.send_invite_email(to_email, token, workspace_name, inviter_name))
        else:
            logger.error(f"Unknown email type: {email_type}")
            if email_log_id:
                async_to_sync(_update_email_log(email_log_id, EmailStatus.FAILED, f"Unknown email type: {email_type}"))
            return
            
        if not success:
            raise Exception("EmailService returned False indicating failure.")
            
        if email_log_id:
            async_to_sync(_update_email_log(email_log_id, EmailStatus.SENT, attempt=self.request.retries + 1))
            
        # Observability logs for success
        log_entry = {
            "event": "email_dispatch",
            "email_log_id": email_log_id,
            "status": "SENT",
            "attempt": self.request.retries + 1
        }
        logger.info(json.dumps(log_entry))
        
    except Exception as exc:
        is_max_retries = self.request.retries >= self.max_retries
        final_status = EmailStatus.FAILED if is_max_retries else EmailStatus.PENDING
        
        if email_log_id:
            async_to_sync(_update_email_log(email_log_id, final_status, str(exc), self.request.retries + 1))
            
        # Observability logs for failure
        log_entry = {
            "event": "email_dispatch",
            "email_log_id": email_log_id,
            "status": "FAILED",
            "attempt": self.request.retries + 1,
            "error": str(exc)
        }
        logger.error(json.dumps(log_entry))
        
        # Exponential backoff retry
        delay = settings.EMAIL_RETRY_BASE_DELAY * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=delay)

async def _process_outbox_batch():
    async with SessionLocal() as db:
        now = datetime.utcnow()
        # Query pending emails ready for sending OR stuck in processing > 5min
        query = select(EmailOutbox).where(
            or_(
                and_(
                    EmailOutbox.status.in_([EmailOutboxStatus.PENDING, EmailOutboxStatus.FAILED]),
                    or_(EmailOutbox.next_attempt_at <= now, EmailOutbox.next_attempt_at == None)
                ),
                and_(
                    EmailOutbox.status == EmailOutboxStatus.PROCESSING,
                    EmailOutbox.locked_at <= now - timedelta(minutes=5)
                )
            )
        ).limit(50).with_for_update(skip_locked=True)
        
        result = await db.execute(query)
        outbox_items = result.scalars().all()
        
        if not outbox_items:
            return
            
        for item in outbox_items:
            item.status = EmailOutboxStatus.PROCESSING
            item.locked_at = now
        
        await db.commit()
        
        for item in outbox_items:
            # Enqueue the robust V2 task
            send_email_task_v2.delay(str(item.id))

@celery_app.task(name="app.workers.email_tasks.process_email_outbox")
def process_email_outbox():
    """Periodic task executed by Beat to poll EmailOutbox and dispatch."""
    async_to_sync(_process_outbox_batch())

@celery_app.task(
    name="app.workers.email_tasks.send_email_task_v2",
    bind=True,
    max_retries=settings.EMAIL_MAX_RETRIES,
    default_retry_delay=settings.EMAIL_RETRY_BASE_DELAY,
    acks_late=True,
    reject_on_worker_lost=True
)
def send_email_task_v2(self, outbox_id: str):
    """
    Idempotent, outbox-driven email dispatcher.
    """
    async def _execute():
        import uuid
        async with SessionLocal() as db:
            outbox = await db.get(EmailOutbox, uuid.UUID(outbox_id) if isinstance(outbox_id, str) else outbox_id)
            if not outbox or outbox.status == EmailOutboxStatus.SENT:
                return
            
            email_log = await db.get(EmailLog, outbox.email_log_id)
            if not email_log:
                outbox.status = EmailOutboxStatus.FAILED
                outbox.last_error = "EmailLog not found"
                await db.commit()
                return
                
            # --- IDEMPOTENCY GUARD ---
            if email_log.status == EmailStatus.SENT or email_log.sent_at:
                outbox.status = EmailOutboxStatus.SENT
                await db.commit()
                return
            
            # --- TWO PHASE LOG STATE GUARD ---
            if email_log.status == EmailStatus.SENDING:
                logger.info(f"Email {email_log.id} is currently SENDING. Short-circuiting retry to prevent duplicates.")
                outbox.status = EmailOutboxStatus.SENT
                await db.commit()
                return
            
            email_type = outbox.email_type
            payload = outbox.payload_json
            to_email = payload.get("to_email")
            
            # --- COMPUTE IDEMPOTENCY KEY & MESSAGE-ID ---
            token_val = payload.get("token", "")
            bucket = outbox.created_at.strftime("%Y%m%d%H")
            raw_key = f"{email_type}:{to_email}:{token_val}:{bucket}"
            ik = hashlib.sha256(raw_key.encode()).hexdigest()
            message_id = f"<{ik}@leadpilot.com>"
            
            if email_log.idempotency_key != ik:
                email_log.idempotency_key = ik
                try:
                    await db.flush()
                except Exception: # UniqueViolation
                    logger.warning(f"Idempotency conflict for {ik}. Already dispatched.")
                    await db.rollback()
                    from sqlalchemy import update
                    import uuid
                    await db.execute(update(EmailOutbox).where(EmailOutbox.id == uuid.UUID(outbox_id)).values(status=EmailOutboxStatus.SENT))
                    await db.commit()
                    return

            # --- MODULE CHECK (Post-Idempotency) ---
            result = await db.execute(select(SystemModuleConfig).where(SystemModuleConfig.module_name == "email_engine"))
            mod = result.scalars().first()
            if mod and not mod.is_enabled:
                email_log.status = EmailStatus.FAILED
                email_log.error_message = "Module email_engine is disabled"
                outbox.status = EmailOutboxStatus.FAILED
                outbox.last_error = "Module email_engine is disabled"
                await db.commit()
                return
            
            # --- PRE-SEND STATE (Two-Phase Commit) ---
            email_log.status = EmailStatus.SENDING
            email_log.provider_message_id = message_id
            await db.commit()
            
            # --- DISPATCH ---
            try:
                success = False
                if email_type == "password_reset":
                    success = await EmailService.send_password_reset_email(to_email, token_val, message_id=message_id, email_log_id=str(email_log.id))
                elif email_type == "workspace_invite":
                    success = await EmailService.send_invite_email(
                        to_email, token_val, payload.get("workspace_name"), payload.get("inviter_name"), message_id=message_id, email_log_id=str(email_log.id)
                    )
                elif email_type == "verify_email":
                    success = await EmailService.send_verification_email(to_email, token_val, message_id=message_id, email_log_id=str(email_log.id))
                else:
                    raise Exception(f"Unknown email type: {email_type}")

                if not success:
                    raise Exception("EmailService returned False indicating failure.")
                
                # --- DB ATOMIC UPDATE ON SUCCESS ---
                email_log.status = EmailStatus.SENT
                email_log.sent_at = datetime.utcnow()
                email_log.attempt_count = outbox.attempt_count + 1
                email_log.error_message = None
                
                outbox.status = EmailOutboxStatus.SENT
                outbox.attempt_count += 1
                outbox.last_error = None
                await db.commit()
                
            except Exception as exc:
                await db.rollback() # Rollback anything in transit
                
                # Safe atomic update for failure status
                async with SessionLocal() as db_err:
                    import uuid
                    err_outbox = await db_err.get(EmailOutbox, uuid.UUID(outbox_id) if isinstance(outbox_id, str) else outbox_id)
                    err_log = await db_err.get(EmailLog, err_outbox.email_log_id)
                    
                    err_outbox.attempt_count += 1
                    err_log.attempt_count = err_outbox.attempt_count
                    
                    is_max = err_outbox.attempt_count >= self.max_retries
                    err_outbox.status = EmailOutboxStatus.FAILED if is_max else EmailOutboxStatus.PENDING
                    
                    if err_log.status != EmailStatus.SENDING:
                        err_log.status = EmailStatus.FAILED if is_max else EmailStatus.PENDING
                    
                    err_outbox.last_error = str(exc)
                    err_log.error_message = str(exc)
                    
                    if not is_max:
                        delay = settings.EMAIL_RETRY_BASE_DELAY * (2 ** err_outbox.attempt_count)
                        err_outbox.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)
                    
                    await db_err.commit()
                
                delay = settings.EMAIL_RETRY_BASE_DELAY * (2 ** outbox.attempt_count)
                raise self.retry(exc=exc, countdown=delay)

    async_to_sync(_execute())
