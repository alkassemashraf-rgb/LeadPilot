# DEPRECATED: execute_instance() and handle_ai_reply() were removed in Mission M-A.
# The ADK runner is now the entry point. See app/core/adk/runner.py.
#
# handle_send_message() and handle_zoho_upsert() are kept here and called by
# the ADK tool closures in app/core/adk/tools.py.

import logging
import hashlib
from typing import Any, Dict
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ExecutionInstance,
    Message,
    Conversation,
    Contact,
    ChannelIdentity,
    Integration,
    ZohoLeadMapping
)
from app.integrations.zoho.adapter import ZohoAdapter
from app.services.runtime_event_service import log_event

logger = logging.getLogger(__name__)


async def handle_zoho_upsert(session: AsyncSession, instance: ExecutionInstance, config: Dict[str, Any]) -> Dict[str, Any]:
    """Upserts lead to Zoho CRM."""
    # 1. Fetch Integration
    integ_query = select(Integration).where(
        Integration.workspace_id == instance.workspace_id,
        Integration.provider == "zoho",
        Integration.status == "connected"
    )
    result = await session.execute(integ_query)
    integration = result.scalars().first()
    if not integration:
        raise Exception("Zoho integration not connected")

    # 2. Fetch Mapping
    mapping_query = select(ZohoLeadMapping).where(ZohoLeadMapping.workspace_id == instance.workspace_id)
    result = await session.execute(mapping_query)
    mapping = result.scalars().first()
    if not mapping or not mapping.field_mappings:
         raise Exception("Zoho mapping not configured")

    # 3. Fetch Contact
    contact = await session.get(Contact, instance.contact_id)
    if not contact:
        raise Exception("Contact not found")

    await log_event(session, event_type="zoho.sync_started", source="zoho",
                    workspace_id=instance.workspace_id,
                    related_ids={"execution_instance_id": str(instance.id), "contact_id": str(instance.contact_id)})

    # 4. Prepare Payload via Service
    from app.services.zoho_payload_builder import build_zoho_payload
    zoho_payload = await build_zoho_payload(
        session,
        instance.contact_id,
        mapping,
        contact,
        overrides=config
    )

    # 5. Execute with Retry Logic
    import json
    import asyncio

    config_dict = {}
    if isinstance(integration.encrypted_config, str):
         config_dict = json.loads(integration.encrypted_config)

    original_config_str = json.dumps(config_dict, sort_keys=True)

    max_retries = 3
    attempt = 0
    zoho_id = None
    action = None

    while attempt < max_retries:
        try:
            attempt += 1
            adapter = ZohoAdapter(integration, config=config_dict)
            zoho_id, action = await adapter.upsert_lead(
                zoho_payload,
                dedupe_strategy=mapping.dedupe_strategy,
                existing_zoho_id=contact.zoho_lead_id
            )
            break
        except Exception as e:
            msg = str(e)
            is_transient = "Error: 5" in msg or "timeout" in msg.lower() or "connection" in msg.lower()

            if is_transient and attempt < max_retries:
                wait_time = 0.5 * (2 ** (attempt - 1))
                logger.warning(f"Zoho Sync transient error (attempt {attempt}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                await log_event(session, event_type="zoho.sync_failed", source="zoho",
                                workspace_id=instance.workspace_id, outcome="failure",
                                error_message=str(e),
                                related_ids={"execution_instance_id": str(instance.id), "contact_id": str(instance.contact_id)})
                raise e

    # Check for Token Refresh
    new_config_str = json.dumps(adapter.config, sort_keys=True)
    if new_config_str != original_config_str:
        integration.encrypted_config = json.dumps(adapter.config)
        session.add(integration)

    # 6. Update Contact
    contact.zoho_lead_id = zoho_id
    contact.zoho_last_synced_at = datetime.utcnow()
    session.add(contact)

    await log_event(session, event_type="zoho.sync_succeeded", source="zoho",
                    workspace_id=instance.workspace_id,
                    related_ids={"execution_instance_id": str(instance.id), "contact_id": str(instance.contact_id)},
                    payload={"zoho_lead_id": zoho_id, "action": action})

    return {"zoho_lead_id": zoho_id, "action": action}


async def handle_send_message(session: AsyncSession, instance: ExecutionInstance, config: Dict[str, Any]) -> Dict[str, Any]:
    """Stores a message record as an outbound intent."""
    content = config.get("content", "")

    conv_result = await session.execute(
        select(Conversation).where(Conversation.contact_id == instance.contact_id)
    )
    conversation = conv_result.scalars().first()

    # Resolve Platform
    identity_result = await session.execute(
        select(ChannelIdentity).where(ChannelIdentity.contact_id == instance.contact_id)
    )
    identity = identity_result.scalars().first()
    platform = identity.provider if identity else "unknown"

    # Compute Idempotency Hash (Mission 6.2)
    recipient_id = identity.provider_user_id if identity else "unknown"
    ident_str = f"{recipient_id}:{content}:{instance.workspace_id}"
    idem_hash = hashlib.sha256(ident_str.encode()).hexdigest()

    new_msg = Message(
        workspace_id=instance.workspace_id,
        conversation_id=conversation.id,
        direction="outbound",
        content=content,
        platform=platform,
        delivery_status="pending",
        is_outbound_intent=True,
        idempotency_hash=idem_hash
    )
    session.add(new_msg)
    await session.flush()

    try:
        from app.workers.tasks import dispatch_message_task
        dispatch_message_task.delay(str(new_msg.id))
    except Exception as e:
        logger.error(f"Failed to trigger dispatch task: {e}")

    return {"status": "intent_stored"}
