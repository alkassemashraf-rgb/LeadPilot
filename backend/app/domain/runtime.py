import logging
import time
import hashlib
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine
from app.models.models import (
    ExecutionInstance, 
    ExecutionStatus, 
    ExecutionStepLog, 
    FlowVersion, 
    Message,
    PromptConfig,
    PromptVersion,
    Conversation, 
    Contact,
    ChannelIdentity,
    ConversationStatus,
    Flow,
    Integration,
    ZohoLeadMapping
)
from app.integrations.zoho.adapter import ZohoAdapter

logger = logging.getLogger(__name__)

async def execute_instance(instance_id: UUID):
    """
    Sequential execution engine for flow instances.
    """
    # Redis lock logic would go here in production
    
    async with AsyncSession(engine) as session:
        instance = await session.get(ExecutionInstance, instance_id)
        if not instance or instance.status != ExecutionStatus.RUNNING:
            return

        # Human Takeover Guard (Mission 7)
        # For ZOHO_UPSERT_LEAD, we might want to ALLOW execution even if takeover
        # Requirements: "If conversation status is HUMAN_TAKEOVER or CLOSED, this node can still run (it is CRM sync, not a reply)."
        # But for MVP simplicity, the current guard BLOCKS everything. 
        # Modifying Guard to peek at next node? Or just blocking for now?
        # Requirement says: "If conversation status is HUMAN_TAKEOVER or CLOSED, this node can still run"
        # Since we don't know the node type until we load the flow... we must load flow first?
        # Or we check status inside the loop?
        # Let's Move the Guard INSIDE the loop for finer control OR just check exception.
        
        # Current Logic: Blocks at start of execute_instance.
        # To support "CRM sync works during takeover", we need to change this.
        # Refactoring execute_instance to Check Node Type before aborting?
        
        # Let's assume for MVP step 1 we stick to guard, BUT we should implement the requirement.
        # To do that, we need to know the current node type.
        pass # Placeholder for diff context

        flow_version = await session.get(FlowVersion, instance.flow_version_id)
        if not flow_version:
            logger.error(f"FlowVersion {instance.flow_version_id} not found")
            return

        definition = flow_version.definition_json
        nodes = definition.get("nodes", [])
        node_map = {str(n["id"]): n for n in nodes}
        
        # ... (rest of setup) ...
        
        # We need the conversation object for the loop check
        conv_query = select(Conversation).where(
            Conversation.contact_id == instance.contact_id,
            Conversation.workspace_id == instance.workspace_id
        )
        conversation = (await session.execute(conv_query)).scalars().first()
        
        # ... (edges logic) ...
        edges = definition.get("edges", [])
        edge_map = {}
        for edge in edges:
            source = str(edge["source_node_id"])
            if source not in edge_map:
                edge_map[source] = []
            edge_map[source].append(str(edge["target_node_id"]))

        current_node_id = str(instance.current_node_id) if instance.current_node_id else None
        
        while current_node_id:
            node = node_map.get(current_node_id)
            if not node:
                break
                
            node_type = node.get("type")
            
            # --- GUARD LOGIC MOVED INSIDE LOOP ---
            # Block AI replies if takeover, but allow system actions like Zoho Sync?
            # Requirement: "If conversation status is HUMAN_TAKEOVER or CLOSED, this node can still run (it is CRM sync, not a reply)."
            # So we abort ONLY if it's an AI_REPLY (or maybe SEND_MESSAGE?) and status is blocked.
            
            if conversation and conversation.status in [ConversationStatus.HUMAN_TAKEOVER, ConversationStatus.CLOSED]:
                # Allow ZOHO_UPSERT_LEAD
                if node_type not in ["ZOHO_UPSERT_LEAD"]:
                    logger.info(f"Flow execution aborted for instance {instance_id}: Conversation status is {conversation.status}")
                    instance.status = ExecutionStatus.ABORTED
                    instance.abort_reason = f"conversation_{conversation.status.value}"
                    instance.aborted_at = datetime.utcnow()
                    session.add(instance)
                    await session.commit()
                    return

            start_time = time.time()
            step_log = ExecutionStepLog(
                execution_instance_id=instance.id,
                node_id=UUID(current_node_id)
            )
            
            try:
                # Execution Logic per Node Type
                output_data = {}
                node_config = node.get("config", {})
                
                if node_type == "AI_REPLY":
                    output_data = await handle_ai_reply(session, instance, node_config)
                elif node_type == "SEND_MESSAGE":
                    output_data = await handle_send_message(session, instance, node_config)
                elif node_type == "ZOHO_UPSERT_LEAD":
                    output_data = await handle_zoho_upsert(session, instance, node_config)
                else:
                    logger.warning(f"Unknown node type: {node_type}")

                step_log.output_data = output_data
                step_log.duration_ms = int((time.time() - start_time) * 1000)
                session.add(step_log)
                
                # Move to next node
                next_nodes = edge_map.get(current_node_id, [])
                if next_nodes:
                    current_node_id = next_nodes[0] # Sequential only in MVP
                    instance.current_node_id = UUID(current_node_id)
                else:
                    current_node_id = None
                    instance.status = ExecutionStatus.COMPLETED
                
                session.add(instance)
                await session.commit()
                
            except Exception as e:
                logger.exception(f"Error executing node {current_node_id}")
                step_log.error_message = str(e)
                instance.status = ExecutionStatus.FAILED
                session.add(step_log)
                session.add(instance)
                await session.commit()
                break

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
        # Fail silently or log error? Logging error in step log seems best.
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

    # 4. Prepare Payload via Service
    from app.services.zoho_payload_builder import build_zoho_payload
    # runtime.py's execute_instance has session, instance...
    # handle_zoho_upsert signature: session, instance, config
    # build_zoho_payload signature: session, contact_id, mapping, contact, overrides
    
    zoho_payload = await build_zoho_payload(
        session, 
        instance.contact_id, 
        mapping, 
        contact,
        overrides=config # config contains node config which might have template
    )

    # 5. Execute with Retry Logic
    import json
    import asyncio
    
    config_dict = {}
    if isinstance(integration.encrypted_config, str):
         config_dict = json.loads(integration.encrypted_config)

    # Snapshot
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
            break # Success
        except Exception as e:
            msg = str(e)
            # Naive check for 5xx in exception string from adapter
            # Adapter: "Zoho API Error: {resp.status_code} - {resp.text}"
            is_transient = "Error: 5" in msg or "timeout" in msg.lower() or "connection" in msg.lower()
            
            if is_transient and attempt < max_retries:
                wait_time = 0.5 * (2 ** (attempt - 1)) # 0.5, 1.0, 2.0
                logger.warning(f"Zoho Sync transient error (attempt {attempt}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise e # Permanent error or max retries

    # Check for Token Refresh
    new_config_str = json.dumps(adapter.config, sort_keys=True)
    if new_config_str != original_config_str:
        integration.encrypted_config = json.dumps(adapter.config)
        session.add(integration)

    # 6. Update Contact
    contact.zoho_lead_id = zoho_id
    contact.zoho_last_synced_at = datetime.utcnow()
    session.add(contact)
    
    return {"zoho_lead_id": zoho_id, "action": action}

async def handle_ai_reply(session: AsyncSession, instance: ExecutionInstance, config: Dict[str, Any]) -> Dict[str, Any]:
    """Generates an AI reply using PromptConfig and Conversation History."""
    # 1. Fetch Prompt Config
    prompt_config_result = await session.execute(
        select(PromptConfig).where(PromptConfig.workspace_id == instance.workspace_id)
    )
    prompt_config = prompt_config_result.scalars().first()
    if not prompt_config or not prompt_config.current_version_id:
        raise Exception("No active PromptConfig found for workspace")
    
    prompt_version = await session.get(PromptVersion, prompt_config.current_version_id)
    
    # 2. Fetch History (Last 15 messages)
    # Find relevant conversation
    conv_result = await session.execute(
        select(Conversation).where(Conversation.contact_id == instance.contact_id)
    )
    conversation = conv_result.scalars().first()
    if not conversation:
        raise Exception("Conversation not found for contact")
        
    msg_result = await session.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc()).limit(15)
    )
    history = msg_result.scalars().all()
    # history is a sequence, need to list it to reverse? sqlmodel returns Sequence.
    # Actually scalars().all() returns a list.
    history = list(history)
    history.reverse()
    
    messages = []
    # System prompt
    messages.append({"role": "system", "content": f"{prompt_version.system_prompt_text}\n\nBusiness Context: {prompt_version.business_profile_json}"})
    
    for msg in history:
        role = "user" if msg.direction == "inbound" else "assistant"
        messages.append({"role": role, "content": msg.content})
    
    # 3. Generate Reply (workspace settings as fallback for model defaults)
    from app.core.ai import ai_provider
    from app.services.settings_service import get_workspace_ai_settings
    ws_ai = await get_workspace_ai_settings(instance.workspace_id, session)
    effective_temp = prompt_version.temperature if prompt_version.temperature != 0.7 else ws_ai.get("temperature", 0.7)
    effective_max_tokens = prompt_version.max_tokens_per_execution if prompt_version.max_tokens_per_execution != 1000 else ws_ai.get("max_tokens", 2048)
    reply_text = await ai_provider.generate_response(
        messages=messages,
        temperature=effective_temp,
        max_tokens=effective_max_tokens
    )
    
    # 4. Resolve Platform from Identity
    identity_result = await session.execute(
        select(ChannelIdentity).where(ChannelIdentity.contact_id == instance.contact_id)
    )
    identity = identity_result.scalars().first()
    platform = identity.provider if identity else "unknown"
    recipient_id = identity.provider_user_id if identity else "unknown"

    # 5. Compute Idempotency Hash (Mission 6.2)
    ident_str = f"{recipient_id}:{reply_text}:{instance.workspace_id}"
    idem_hash = hashlib.sha256(ident_str.encode()).hexdigest()

    # 6. Store as Message (Outbound)
    new_msg = Message(
        workspace_id=instance.workspace_id,
        conversation_id=conversation.id,
        direction="outbound",
        content=reply_text,
        platform=platform,
        delivery_status="pending",
        is_outbound_intent=True,
        idempotency_hash=idem_hash
    )
    session.add(new_msg)
    await session.flush() # Get the ID for Celery

    # 6. Trigger Dispatch (Mission 6)
    try:
        from app.workers.tasks import dispatch_message_task
        dispatch_message_task.delay(str(new_msg.id))
    except Exception as e:
        logger.error(f"Failed to trigger dispatch task: {e}")

    return {"reply": reply_text}

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
