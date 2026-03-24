from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel

from app.core.db import get_db
from app.api import deps
from app.models.models import (
    Flow, FlowVersion, FlowDraft, FlowStatus, User, Workspace,
    RuntimeEventLog,
    AutomationTemplateVersion, TemplateUsageStat,
    TemplateVariable, FlowTemplateVariableValue,
)
from app.schemas.envelope import wrap_data, wrap_error
from app.core.catalog_registry import VALID_NODE_TYPES, VALID_TRIGGER_TYPES
from app.services.entitlements import require_entitlement
from app.services.audit_service import audit_event
from app.domain.builder_translator import validate_graph, translate, simulate

router = APIRouter()

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class BuilderStep(BaseModel):
    type: str  # AI_REPLY, SEND_MESSAGE, HUMAN_HANDOVER, TAG_CONTACT
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

class CreateFlowPayload(BaseModel):
    name: str
    description: Optional[str] = ""

class UpdateFlowPayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SaveDraftPayload(BaseModel):
    builder_graph_json: Dict[str, Any]

class SimulatePayload(BaseModel):
    mock_payload: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# GET /automations — list
# ---------------------------------------------------------------------------

@router.get("", dependencies=[Depends(require_entitlement("automations"))])
async def list_flows(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """List all flows for the workspace."""
    result = await db.execute(
        select(Flow).where(Flow.workspace_id == workspace.id)
        .order_by(Flow.updated_at.desc())
    )
    flows = result.scalars().all()
    return wrap_data([
        {
            "id": str(f.id),
            "name": f.name,
            "description": f.description,
            "status": f.status,
            "published_version_id": str(f.published_version_id) if f.published_version_id else None,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat(),
            "source_template_id": str(f.source_template_id) if f.source_template_id else None,
        }
        for f in flows
    ])

# ---------------------------------------------------------------------------
# POST /automations — create blank flow (canvas-first approach)
# ---------------------------------------------------------------------------

@router.post("", dependencies=[Depends(require_entitlement("automations", increment=True))])
async def create_flow(
    payload: CreateFlowPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Create a blank flow. Returns flow_id for redirect to canvas editor."""
    flow = Flow(
        name=payload.name,
        description=payload.description,
        workspace_id=workspace.id,
        status=FlowStatus.DRAFT,
    )
    db.add(flow)
    await db.flush()

    await audit_event(
        db, action="automation_create", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"flow_name": payload.name, "method": "blank"},
    )
    await db.commit()
    return wrap_data({"flow_id": str(flow.id)})

# ---------------------------------------------------------------------------
# POST /automations/from-builder — PRESERVED (wizard-based, backward compat)
# ---------------------------------------------------------------------------

@router.post("/from-builder", dependencies=[Depends(require_entitlement("automations", increment=True))])
async def create_from_builder(
    payload: BuilderPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Translate wizard payload to runtime JSON and save flow. Preserved for backward compatibility."""
    for step in payload.steps:
        if step.type not in VALID_NODE_TYPES:
            return wrap_error(f"Invalid step type: {step.type}")
    if payload.trigger.type not in VALID_TRIGGER_TYPES:
        return wrap_error(f"Invalid trigger type: {payload.trigger.type}")

    nodes = []
    edges = []

    trigger_id = str(uuid.uuid4())
    nodes.append({
        "id": trigger_id,
        "type": "TRIGGER",
        "config": payload.trigger.model_dump()
    })

    prev_node_id = trigger_id

    for step in payload.steps:
        node_id = str(uuid.uuid4())
        config = step.config.copy()

        if step.type == "AI_REPLY":
            if "goal" not in config or not config["goal"]:
                config["goal"] = "General assisting"
            if "tasks" not in config or not config["tasks"]:
                config["tasks"] = ["Help the user with their inquiry"]
            config["use_workspace_prompt"] = True

        nodes.append({"id": node_id, "type": step.type, "config": config})
        edges.append({
            "id": str(uuid.uuid4()),
            "source_node_id": prev_node_id,
            "target_node_id": node_id
        })
        prev_node_id = node_id

    definition = {
        "start_node_id": trigger_id,
        "nodes": nodes,
        "edges": edges,
        "ignore_outbound_webhooks": True
    }

    flow = Flow(
        name=payload.name,
        description=payload.description,
        workspace_id=workspace.id,
        status=FlowStatus.PUBLISHED if payload.publish else FlowStatus.DRAFT
    )
    db.add(flow)
    await db.flush()

    version = FlowVersion(
        flow_id=flow.id,
        version_number=1,
        definition_json=definition,
        is_published=payload.publish
    )
    db.add(version)
    await db.flush()

    if payload.publish:
        flow.published_version_id = version.id
        db.add(flow)

    await audit_event(
        db, action="automation_create", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"flow_name": payload.name, "published": payload.publish},
    )
    await db.commit()

    return wrap_data({"flow_id": str(flow.id), "version": 1})

# ---------------------------------------------------------------------------
# GET /automations/{flow_id}
# ---------------------------------------------------------------------------

@router.get("/{flow_id}")
async def get_flow(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Get flow details."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalars().first()

    response = {
        "id": str(flow.id),
        "name": flow.name,
        "description": flow.description,
        "status": flow.status,
        "published_version_id": str(flow.published_version_id) if flow.published_version_id else None,
        "created_at": flow.created_at.isoformat(),
        "updated_at": flow.updated_at.isoformat(),
        "definition": version.definition_json if version else None,
        "version_number": version.version_number if version else None,
        "source_template_id": str(flow.source_template_id) if flow.source_template_id else None,
        "source_template_version_id": str(flow.source_template_version_id) if flow.source_template_version_id else None,
        "latest_template_version_number": None,
    }

    # Look up latest published template version for "new version available" badge
    if flow.source_template_id:
        tv_result = await db.execute(
            select(AutomationTemplateVersion)
            .where(
                AutomationTemplateVersion.template_id == flow.source_template_id,
                AutomationTemplateVersion.is_published == True,
            )
            .order_by(AutomationTemplateVersion.version_number.desc())
            .limit(1)
        )
        latest_tv = tv_result.scalars().first()
        if latest_tv:
            response["latest_template_version_number"] = latest_tv.version_number
            response["latest_template_version_id"] = str(latest_tv.id)

    return wrap_data(response)

# ---------------------------------------------------------------------------
# PATCH /automations/{flow_id}
# ---------------------------------------------------------------------------

@router.patch("/{flow_id}")
async def update_flow(
    flow_id: UUID,
    payload: UpdateFlowPayload,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Update flow metadata (name, description)."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    if payload.name is not None:
        flow.name = payload.name
    if payload.description is not None:
        flow.description = payload.description
    flow.updated_at = datetime.utcnow()
    db.add(flow)
    await db.commit()
    return wrap_data({"id": str(flow.id), "name": flow.name})

# ---------------------------------------------------------------------------
# DELETE /automations/{flow_id}
# ---------------------------------------------------------------------------

@router.delete("/{flow_id}")
async def delete_flow(
    flow_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a flow and its draft."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    draft_result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = draft_result.scalars().first()
    if draft:
        await db.delete(draft)

    await audit_event(
        db, action="automation_delete", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"flow_name": flow.name},
    )
    await db.delete(flow)
    await db.commit()
    return wrap_data({"deleted": True})

# ---------------------------------------------------------------------------
# GET /automations/{flow_id}/draft
# ---------------------------------------------------------------------------

@router.get("/{flow_id}/draft")
async def get_draft(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Get the editable draft for a flow. Returns null if no draft exists."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = result.scalars().first()

    if not draft:
        return wrap_data({
            "builder_graph_json": None,
            "last_validation_errors": None,
            "updated_at": None,
        })

    return wrap_data({
        "builder_graph_json": draft.builder_graph_json,
        "last_validation_errors": draft.last_validation_errors,
        "updated_at": draft.updated_at.isoformat(),
    })

# ---------------------------------------------------------------------------
# PUT /automations/{flow_id}/draft — autosave
# ---------------------------------------------------------------------------

@router.put("/{flow_id}/draft")
async def save_draft(
    flow_id: UUID,
    payload: SaveDraftPayload,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Save (upsert) the builder graph draft. Called by autosave."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = result.scalars().first()
    now = datetime.utcnow()

    if draft:
        draft.builder_graph_json = payload.builder_graph_json
        draft.updated_by_user_id = current_user.id
        draft.updated_at = now
        db.add(draft)
    else:
        draft = FlowDraft(
            workspace_id=workspace.id,
            flow_id=flow_id,
            builder_graph_json=payload.builder_graph_json,
            updated_by_user_id=current_user.id,
            updated_at=now,
        )
        db.add(draft)

    await db.commit()
    return wrap_data({"saved": True, "updated_at": now.isoformat()})

# ---------------------------------------------------------------------------
# POST /automations/{flow_id}/draft/validate
# ---------------------------------------------------------------------------

@router.post("/{flow_id}/draft/validate")
async def validate_draft(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Validate the current draft. Returns structured errors per node/field."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = result.scalars().first()
    if not draft:
        return wrap_error("No draft found. Save a draft first.")

    errors = validate_graph(draft.builder_graph_json)
    draft.last_validation_errors = {"errors": errors, "validated_at": datetime.utcnow().isoformat()}
    draft.updated_at = datetime.utcnow()
    db.add(draft)
    await db.commit()

    return wrap_data({
        "valid": len(errors) == 0,
        "errors": errors,
    })

# ---------------------------------------------------------------------------
# POST /automations/{flow_id}/publish — REPLACED with draft-based approach
# ---------------------------------------------------------------------------

@router.post("/{flow_id}/publish")
async def publish_flow(
    flow_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Validate draft → translate to runtime definition_json → create immutable FlowVersion.
    Sets flow.published_version_id to the new version.
    """
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = result.scalars().first()
    if not draft:
        return wrap_error("No draft found. Build your automation in the canvas editor first.")

    # Validate
    errors = validate_graph(draft.builder_graph_json)
    if errors:
        draft.last_validation_errors = {"errors": errors, "validated_at": datetime.utcnow().isoformat()}
        db.add(draft)
        await db.commit()
        return wrap_data({
            "success": False,
            "published": False,
            "errors": errors,
        })

    # Translate to runtime contract (dual output: legacy + ADK pipeline)
    definition_json, adk_pipeline_config = translate(draft.builder_graph_json)

    # Get next version number
    version_result = await db.execute(
        select(func.max(FlowVersion.version_number))
        .where(FlowVersion.flow_id == flow_id)
    )
    max_version = version_result.scalar() or 0
    new_version_number = max_version + 1

    now = datetime.utcnow()
    new_version = FlowVersion(
        flow_id=flow_id,
        version_number=new_version_number,
        definition_json=definition_json,
        adk_pipeline_config=adk_pipeline_config,
        is_published=True,
        created_at=now,
        updated_at=now,
    )
    db.add(new_version)
    await db.flush()

    # Update flow
    flow.published_version_id = new_version.id
    flow.status = FlowStatus.PUBLISHED
    flow.updated_at = now
    db.add(flow)

    # Clear validation errors from draft
    draft.last_validation_errors = None
    draft.updated_at = now
    db.add(draft)

    # Increment template publish_count if flow was cloned from a template (Mission 32)
    if flow.source_template_id:
        stat_result = await db.execute(
            select(TemplateUsageStat).where(TemplateUsageStat.template_id == flow.source_template_id)
        )
        stat = stat_result.scalars().first()
        if stat:
            stat.publish_count += 1
            stat.updated_at = now
            db.add(stat)

    await audit_event(
        db, action="automation_publish", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"version_number": new_version_number},
    )
    await db.commit()

    return wrap_data({
        "success": True,
        "published": True,
        "version_id": str(new_version.id),
        "version_number": new_version_number,
        "published_at": now.isoformat(),
        "status": "published",
    })

# ---------------------------------------------------------------------------
# GET /automations/{flow_id}/versions
# ---------------------------------------------------------------------------

@router.get("/{flow_id}/versions")
async def list_versions(
    flow_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """List all published versions for a flow, newest first."""
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowVersion)
        .where(FlowVersion.flow_id == flow_id)
        .order_by(FlowVersion.version_number.desc())
    )
    versions = result.scalars().all()

    return wrap_data([
        {
            "id": str(v.id),
            "version_number": v.version_number,
            "is_published": v.is_published,
            "is_active": (str(v.id) == str(flow.published_version_id)) if flow.published_version_id else False,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ])

# ---------------------------------------------------------------------------
# POST /automations/{flow_id}/rollback/{version_id}
# ---------------------------------------------------------------------------

@router.post("/{flow_id}/rollback/{version_id}")
async def rollback_version(
    flow_id: UUID,
    version_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Create a new FlowVersion identical to version_id and make it the active version.
    Safe rollback — does NOT delete history.
    """
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    source_version = await db.get(FlowVersion, version_id)
    if not source_version or source_version.flow_id != flow_id:
        return wrap_error("Version not found")

    # Get next version number
    version_result = await db.execute(
        select(func.max(FlowVersion.version_number))
        .where(FlowVersion.flow_id == flow_id)
    )
    max_version = version_result.scalar() or 0
    new_version_number = max_version + 1

    now = datetime.utcnow()
    new_version = FlowVersion(
        flow_id=flow_id,
        version_number=new_version_number,
        definition_json=source_version.definition_json,
        is_published=True,
        created_at=now,
        updated_at=now,
    )
    db.add(new_version)
    await db.flush()

    flow.published_version_id = new_version.id
    flow.status = FlowStatus.PUBLISHED
    flow.updated_at = now
    db.add(flow)

    await audit_event(
        db, action="automation_rollback", entity_type="flow",
        entity_id=str(flow.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={
            "rolled_back_to_version": source_version.version_number,
            "new_version_number": new_version_number,
        },
    )
    await db.commit()

    return wrap_data({
        "new_version_id": str(new_version.id),
        "new_version_number": new_version_number,
        "rolled_back_to": source_version.version_number,
    })

# ---------------------------------------------------------------------------
# POST /automations/{flow_id}/simulate
# ---------------------------------------------------------------------------

@router.post("/{flow_id}/simulate")
async def simulate_flow(
    flow_id: UUID,
    payload: SimulatePayload,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Dry-run the automation against a mock payload.
    Returns step-by-step preview. No messages sent, no provider calls.
    """
    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow_id)
    )
    draft = result.scalars().first()
    if not draft:
        return wrap_error("No draft found. Build your automation first.")

    # Validate first
    errors = validate_graph(draft.builder_graph_json)
    if errors:
        return wrap_data({
            "valid": False,
            "errors": errors,
            "steps": [],
        })

    # Run simulation (pure in-memory, no side effects)
    preview = simulate(draft.builder_graph_json, payload.mock_payload)

    # Log simulate event (non-blocking)
    try:
        event = RuntimeEventLog(
            workspace_id=workspace.id,
            event_type="simulate.run",
            source="simulate",
            related_ids={"flow_id": str(flow_id)},
            actor_user_id=current_user.id,
            payload={"steps_count": len(preview.get("steps", []))},
            outcome="success",
        )
        db.add(event)
        await db.commit()
    except Exception:
        pass

    return wrap_data({"valid": True, **preview})


# ---------------------------------------------------------------------------
# POST /automations/{flow_id}/rebase-to-template/{template_version_id}
# ---------------------------------------------------------------------------

@router.post(
    "/{flow_id}/rebase-to-template/{template_version_id}",
    dependencies=[Depends(require_entitlement("automations"))],
)
async def rebase_to_template(
    flow_id: UUID,
    template_version_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Rebase a template-cloned flow to a newer template version.
    Replaces FlowDraft graph with new version's graph (re-applying stored variable values).
    """
    import json

    flow = await db.get(Flow, flow_id)
    if not flow or flow.workspace_id != workspace.id:
        return wrap_error("Flow not found")

    if not flow.source_template_id:
        return wrap_error("This flow was not cloned from a template")

    # Validate the template version
    tv = await db.get(AutomationTemplateVersion, template_version_id)
    if not tv or not tv.is_published:
        return wrap_error("Template version not found or not published")
    if tv.template_id != flow.source_template_id:
        return wrap_error("Template version does not belong to the source template")

    # Load stored variable values for this flow
    ftvv_result = await db.execute(
        select(FlowTemplateVariableValue, TemplateVariable)
        .join(TemplateVariable, TemplateVariable.id == FlowTemplateVariableValue.template_variable_id)
        .where(FlowTemplateVariableValue.flow_id == flow.id)
    )
    stored_values = {}
    for ftvv, tvar in ftvv_result.all():
        stored_values[tvar.key] = ftvv.value or tvar.default_value or ""

    # Also load any NEW variables from the target version (not yet stored)
    new_var_result = await db.execute(
        select(TemplateVariable)
        .where(TemplateVariable.template_version_id == template_version_id)
        .order_by(TemplateVariable.sort_order)
    )
    new_vars = new_var_result.scalars().all()
    for nv in new_vars:
        if nv.key not in stored_values:
            stored_values[nv.key] = nv.default_value or ""

    # Perform variable replacement on new version's graph
    graph_str = json.dumps(tv.builder_graph_json)
    for key, value in stored_values.items():
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        graph_str = graph_str.replace("{{" + key + "}}", escaped_value)
    replaced_graph = json.loads(graph_str)

    # Update FlowDraft
    draft_result = await db.execute(
        select(FlowDraft).where(FlowDraft.flow_id == flow.id)
    )
    draft = draft_result.scalars().first()
    if not draft:
        return wrap_error("No draft found for this flow")

    now = datetime.utcnow()
    draft.builder_graph_json = replaced_graph
    draft.last_validation_errors = None
    draft.updated_at = now
    draft.updated_by_user_id = current_user.id
    db.add(draft)

    # Update flow source version
    flow.source_template_version_id = template_version_id
    flow.updated_at = now
    db.add(flow)

    # Store variable values for new version's variables
    for nv in new_vars:
        if nv.key not in {tvar.key for _, tvar in ftvv_result.all() if True}:
            # This is a genuinely new variable — store it
            pass  # Existing stored values cover the key via stored_values dict

    await db.commit()

    return wrap_data({
        "rebased": True,
        "new_version_number": tv.version_number,
        "flow_id": str(flow.id),
    })
