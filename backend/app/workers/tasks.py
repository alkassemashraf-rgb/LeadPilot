import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.db import engine
from app.models.models import WebhookEventLog, WebhookStatus
from sqlmodel import Session, select

logger = get_task_logger(__name__)

def run_async(coro):
    """Helper to run async code in sync celery worker."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

from app.models.models import (
    WebhookEventLog,
    WebhookStatus,
    Message,
    FlowVersion,
    ExecutionInstance,
    ExecutionStatus,
    Flow,
    Conversation
)
from app.domain.contacts import resolve_or_create_contact
from app.domain.runtime import execute_instance
from app.services.dispatch_service import DispatchService

logger = get_task_logger(__name__)

def parse_webhook_payload(provider: str, payload: Dict) -> Dict:
    """Extract normalized fields from provider payloads."""
    normalized = {
        "trigger_type": None,
        "provider_user_id": None,
        "content": None,
        "first_name": None
    }
    
    try:
        if provider == "whatsapp":
            entry = payload.get("entry", [])[0]
            value = entry.get("changes", [])[0].get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])
            
            if messages:
                msg = messages[0]
                normalized["trigger_type"] = "MESSAGE_INBOUND"
                normalized["provider_user_id"] = msg.get("from")
                normalized["content"] = msg.get("text", {}).get("body")
                if contacts:
                    normalized["first_name"] = contacts[0].get("profile", {}).get("name")
        
        elif provider == "meta":
            entry = payload.get("entry", [])[0]
            # Messaging (Messenger/Instagram)
            if "messaging" in entry:
                msg_event = entry["messaging"][0]
                normalized["trigger_type"] = "MESSAGE_INBOUND"
                normalized["provider_user_id"] = msg_event.get("sender", {}).get("id")
                normalized["content"] = msg_event.get("message", {}).get("text")
            # Lead Ads
            elif "changes" in entry:
                change = entry["changes"][0]
                if change.get("field") == "leadgen":
                    normalized["trigger_type"] = "LEAD_AD_SUBMIT"
                    normalized["provider_user_id"] = change.get("value", {}).get("leadgen_id")
                    normalized["content"] = "Lead Ad Submission"
    except (IndexError, KeyError, AttributeError):
        pass
        
    return normalized

@celery_app.task(name="app.workers.tasks.process_webhook_event")
def process_webhook_event(event_id: str):
    """
    Process a stored webhook event and trigger automation flows.
    """
    async def _run():
        logger.info(f"Processing webhook event: {event_id}")
        from app.core.db import engine
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.services.runtime_event_service import log_event

        async with AsyncSession(engine) as session:
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
                if event.provider == "whatsapp":
                    value = event.payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
                    if "statuses" in value and "messages" not in value:
                        logger.info(f"Ignoring WhatsApp status update {event_id}")
                        event.status = WebhookStatus.PROCESSED
                        session.add(event)
                        await session.commit()
                        return

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
                if not info["trigger_type"]:
                    logger.info(f"No actionable trigger found in payload for event {event_id}")
                    event.status = WebhookStatus.PROCESSED
                    session.add(event)
                    await session.commit()
                    return

                # 2. Resolve Contact & Store Message
                contact, identity, conversation = await resolve_or_create_contact(
                    session,
                    event.workspace_id,
                    event.provider,
                    info["provider_user_id"],
                    first_name=info["first_name"]
                )

                if info["trigger_type"] == "MESSAGE_INBOUND":
                    inbound_msg = Message(
                        workspace_id=event.workspace_id,
                        conversation_id=conversation.id,
                        direction="inbound",
                        content=info["content"] or "",
                        platform=event.provider,
                        delivery_status="delivered"
                    )
                    session.add(inbound_msg)

                # 3. Find Matching Published Flow
                flow_query = select(FlowVersion).join(Flow).where(
                    Flow.workspace_id == event.workspace_id,
                    FlowVersion.is_published == True
                ).order_by(FlowVersion.created_at.desc())

                flow_version = (await session.execute(flow_query)).scalars().first()

                if flow_version:
                    # 4. Create Execution Instance
                    nodes = flow_version.definition_json.get("nodes", [])
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

                    # 5. Execute Runtime
                    await execute_instance(instance.id)

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
    from app.core.db import engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _run():
        async with AsyncSession(engine) as session:
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
    from app.core.db import engine
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _run():
        async with AsyncSession(engine) as session:
            await DispatchService.dispatch_pending_messages(
                session,
                workspace_id=UUID(workspace_id) if workspace_id else None
            )

    run_async(_run())


@celery_app.task(name="app.workers.tasks.purge_runtime_events_task")
def purge_runtime_events_task():
    """Daily task to purge old runtime events based on retention policy."""
    from app.core.config import settings as app_settings
    from app.core.db import engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.models import RuntimeEventLog
    from datetime import timedelta
    from sqlalchemy import delete as sa_delete

    async def _run():
        cutoff = datetime.utcnow() - timedelta(days=app_settings.RUNTIME_EVENT_RETENTION_DAYS)
        total_purged = 0
        async with AsyncSession(engine) as session:
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
