from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.core.db import get_db
from app.api import deps
from app.models.models import Flow, FlowVersion, FlowStatus, User, Workspace
from app.api.v1.auth import login # Keeping this if needed, or just remove if unused
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.catalog_registry import VALID_NODE_TYPES, VALID_TRIGGER_TYPES
from app.services.entitlements import require_entitlement
from app.services.audit_service import audit_event

router = APIRouter()

class BuilderStep(BaseModel):
    type: str # AI_REPLY, SEND_MESSAGE, HUMAN_HANDOVER, TAG_CONTACT
    config: Dict[str, Any]

class BuilderTrigger(BaseModel):
    type: str
    platform: str
    keywords: Optional[List[str]] = []

class BuilderPayload(BaseModel):
    name: str
    description: Optional[str] = ""
    trigger: BuilderTrigger
    steps: List[BuilderStep]
    publish: bool = False

@router.get("", dependencies=[Depends(require_entitlement("automations"))])
async def list_flows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """List all flows for the workspace."""
    result = await db.execute(select(Flow))
    return wrap_data(result.scalars().all())

@router.post("/from-builder", dependencies=[Depends(require_entitlement("automations", increment=True))])
async def create_from_builder(
    payload: BuilderPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Translate wizard payload to runtime JSON and save flow."""
    # Validate step and trigger types against catalog registry
    for step in payload.steps:
        if step.type not in VALID_NODE_TYPES:
            return wrap_error(f"Invalid step type: {step.type}")
    if payload.trigger.type not in VALID_TRIGGER_TYPES:
        return wrap_error(f"Invalid trigger type: {payload.trigger.type}")

    # 1. Translation Logic
    nodes = []
    edges = []
    
    # Trigger Node
    trigger_id = str(uuid.uuid4())
    nodes.append({
        "id": trigger_id,
        "type": "TRIGGER",
        "config": payload.trigger.model_dump()
    })
    
    prev_node_id = trigger_id
    
    # Action Nodes
    for step in payload.steps:
        node_id = str(uuid.uuid4())
        config = step.config.copy()
        
        # Default AI config hardening (Mission 5.3)
        if step.type == "AI_REPLY":
            if "goal" not in config or not config["goal"]:
                config["goal"] = "General assisting"
            if "tasks" not in config or not config["tasks"]:
                config["tasks"] = ["Help the user with their inquiry"]
            
            config["use_workspace_prompt"] = True
        
        nodes.append({
            "id": node_id,
            "type": step.type,
            "config": config
        })
        
        # Sequentially link
        edges.append({
            "id": str(uuid.uuid4()),
            "source_node_id": prev_node_id,
            "target_node_id": node_id
        })
        prev_node_id = node_id
        
    definition = {
        "nodes": nodes,
        "edges": edges,
        "ignore_outbound_webhooks": True
    }
    
    # 2. Save Flow
    flow = Flow(
        name=payload.name,
        description=payload.description,
        workspace_id=workspace.id,
        status=FlowStatus.PUBLISHED if payload.publish else FlowStatus.DRAFT
    )
    db.add(flow)
    await db.flush()
    
    # 3. Create Version
    version = FlowVersion(
        flow_id=flow.id,
        version_number=1,
        definition_json=definition,
        is_published=payload.publish
    )
    db.add(version)
    await audit_event(
        db, action="automation_create", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"flow_name": payload.name, "published": payload.publish},
    )
    await db.commit()

    return wrap_data({"flow_id": str(flow.id), "version": 1})

@router.get("/{flow_id}")
async def get_flow(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get flow along with its summary definition."""
    flow = await db.get(Flow, flow_id)
    if not flow:
        return wrap_error("Flow not found")
    
    result = await db.execute(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalars().first()
    
    return wrap_data({
        "id": flow.id,
        "name": flow.name,
        "description": flow.description,
        "status": flow.status,
        "definition": version.definition_json if version else None
    })

@router.post("/{flow_id}/publish")
async def publish_flow(
    flow_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Publish a flow version."""
    flow = await db.get(Flow, flow_id)
    if not flow:
        return wrap_error("Flow not found")
    
    result = await db.execute(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
        .limit(1)
    )
    last_version = result.scalars().first()
    
    if not last_version:
        return wrap_error("No version found to publish")
        
    last_version.is_published = True
    flow.status = FlowStatus.PUBLISHED
    
    db.add(last_version)
    db.add(flow)
    await audit_event(
        db, action="automation_publish", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=flow.workspace_id, request=request,
    )
    await db.commit()

    return wrap_data({"status": "published"})
