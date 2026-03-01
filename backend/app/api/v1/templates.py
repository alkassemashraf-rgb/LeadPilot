"""
Template Catalog API — Mission 27 + Mission 32

Workspace-facing endpoints for browsing and cloning automation templates.
Admin-facing endpoints are in admin.py.
"""
import json
from typing import Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.core.db import get_db
from app.api import deps
from app.models.models import (
    AutomationTemplate, AutomationTemplateVersion,
    Flow, FlowDraft, FlowStatus,
    Workspace, User, RuntimeEventLog,
    TemplateVariable, FlowTemplateVariableValue, TemplateUsageStat,
)
from app.schemas.envelope import wrap_data, wrap_error
from app.services.entitlements import require_entitlement

router = APIRouter()


class CloneTemplatePayload(BaseModel):
    name: Optional[str] = None  # Defaults to template name if not provided
    variable_values: Optional[Dict[str, str]] = None  # {"business_name": "Acme Inc"}


# ---------------------------------------------------------------------------
# GET /templates — browse the catalog
# ---------------------------------------------------------------------------

@router.get("", dependencies=[Depends(require_entitlement("automations"))])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
    category: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    featured: Optional[bool] = Query(None),
    sort: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all active templates with optional filters."""
    query = (
        select(AutomationTemplate, TemplateUsageStat)
        .outerjoin(TemplateUsageStat, TemplateUsageStat.template_id == AutomationTemplate.id)
        .where(AutomationTemplate.is_active == True)
    )

    if category:
        query = query.where(AutomationTemplate.category == category)
    if featured is not None:
        query = query.where(AutomationTemplate.is_featured == featured)

    if sort == "popular":
        query = query.order_by(
            TemplateUsageStat.clone_count.desc().nulls_last(),
            AutomationTemplate.name.asc()
        )
    else:
        query = query.order_by(
            AutomationTemplate.is_featured.desc(),
            AutomationTemplate.name.asc()
        )

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Platform filter is done in Python since platforms is a JSON array
    if platform:
        rows = [(t, s) for t, s in rows if platform in (t.platforms or [])]

    return wrap_data([
        {
            "id": str(t.id),
            "slug": t.slug,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "industry_tags": t.industry_tags or [],
            "platforms": t.platforms or [],
            "required_integrations": t.required_integrations or [],
            "is_featured": t.is_featured,
            "clone_count": s.clone_count if s else 0,
        }
        for t, s in rows
    ])


# ---------------------------------------------------------------------------
# GET /templates/{slug} — template detail with latest published version
# ---------------------------------------------------------------------------

@router.get("/{slug}", dependencies=[Depends(require_entitlement("automations"))])
async def get_template(
    slug: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Get template detail including latest published version."""
    result = await db.execute(
        select(AutomationTemplate)
        .where(AutomationTemplate.slug == slug, AutomationTemplate.is_active == True)
    )
    template = result.scalars().first()
    if not template:
        return wrap_error("Template not found")

    # Latest published version
    version_result = await db.execute(
        select(AutomationTemplateVersion)
        .where(
            AutomationTemplateVersion.template_id == template.id,
            AutomationTemplateVersion.is_published == True,
        )
        .order_by(AutomationTemplateVersion.version_number.desc())
        .limit(1)
    )
    latest_version = version_result.scalars().first()

    # Load variables for the latest published version (Mission 32)
    variables_data = []
    if latest_version:
        var_result = await db.execute(
            select(TemplateVariable)
            .where(TemplateVariable.template_version_id == latest_version.id)
            .order_by(TemplateVariable.sort_order)
        )
        variables_data = [
            {
                "key": v.key,
                "label": v.label,
                "description": v.description,
                "var_type": v.var_type,
                "required": v.required,
                "default_value": v.default_value,
            }
            for v in var_result.scalars().all()
        ]

    # Clone count
    stat_result = await db.execute(
        select(TemplateUsageStat).where(TemplateUsageStat.template_id == template.id)
    )
    stat = stat_result.scalars().first()

    return wrap_data({
        "id": str(template.id),
        "slug": template.slug,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "industry_tags": template.industry_tags or [],
        "platforms": template.platforms or [],
        "required_integrations": template.required_integrations or [],
        "is_featured": template.is_featured,
        "clone_count": stat.clone_count if stat else 0,
        "variables": variables_data,
        "latest_version": {
            "id": str(latest_version.id),
            "version_number": latest_version.version_number,
            "builder_graph_json": latest_version.builder_graph_json,
            "changelog": latest_version.changelog,
            "published_at": latest_version.published_at.isoformat() if latest_version.published_at else None,
        } if latest_version else None,
    })


# ---------------------------------------------------------------------------
# POST /templates/{slug}/clone — clone template into workspace
# ---------------------------------------------------------------------------

@router.post(
    "/{slug}/clone",
    dependencies=[Depends(require_entitlement("automations", increment=True))],
)
async def clone_template(
    slug: str,
    payload: CloneTemplatePayload,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Clone a template into the current workspace as a new Flow + FlowDraft.
    Supports variable replacement: supply variable_values to replace {{key}} placeholders.
    """
    # Load template
    result = await db.execute(
        select(AutomationTemplate)
        .where(AutomationTemplate.slug == slug, AutomationTemplate.is_active == True)
    )
    template = result.scalars().first()
    if not template:
        return wrap_error("Template not found")

    # Load latest published version
    version_result = await db.execute(
        select(AutomationTemplateVersion)
        .where(
            AutomationTemplateVersion.template_id == template.id,
            AutomationTemplateVersion.is_published == True,
        )
        .order_by(AutomationTemplateVersion.version_number.desc())
        .limit(1)
    )
    latest_version = version_result.scalars().first()
    if not latest_version:
        return wrap_error("Template has no published version yet. Check back later.")

    # Load variables for this version (Mission 32)
    var_result = await db.execute(
        select(TemplateVariable)
        .where(TemplateVariable.template_version_id == latest_version.id)
        .order_by(TemplateVariable.sort_order)
    )
    var_list = var_result.scalars().all()

    # Validate required variables
    supplied = payload.variable_values or {}
    if var_list:
        for v in var_list:
            if v.required and v.key not in supplied and not v.default_value:
                return wrap_error(f"Required variable '{v.label}' ({v.key}) is missing")

    # Perform variable replacement in builder_graph_json
    graph_str = json.dumps(latest_version.builder_graph_json)
    if var_list:
        for v in var_list:
            value = supplied.get(v.key, v.default_value or "")
            # Escape for JSON string safety
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            graph_str = graph_str.replace("{{" + v.key + "}}", escaped_value)
    replaced_graph = json.loads(graph_str)

    # Create new flow in workspace
    flow_name = (payload.name or "").strip() or template.name
    now = datetime.utcnow()

    flow = Flow(
        name=flow_name,
        description=template.description,
        workspace_id=workspace.id,
        status=FlowStatus.DRAFT,
        source_template_id=template.id,
        source_template_version_id=latest_version.id,
        created_at=now,
        updated_at=now,
    )
    db.add(flow)
    await db.flush()

    # Create draft from (possibly variable-replaced) builder_graph_json
    draft = FlowDraft(
        workspace_id=workspace.id,
        flow_id=flow.id,
        builder_graph_json=replaced_graph,
        updated_by_user_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)

    # Store variable values (Mission 32)
    for v in var_list:
        ftvv = FlowTemplateVariableValue(
            flow_id=flow.id,
            template_variable_id=v.id,
            value=supplied.get(v.key, v.default_value),
            created_at=now,
            updated_at=now,
        )
        db.add(ftvv)

    # Increment clone_count (Mission 32)
    stat_result = await db.execute(
        select(TemplateUsageStat).where(TemplateUsageStat.template_id == template.id)
    )
    stat = stat_result.scalars().first()
    if stat:
        stat.clone_count += 1
        stat.updated_at = now
        db.add(stat)

    # Log the clone event
    try:
        event = RuntimeEventLog(
            workspace_id=workspace.id,
            event_type="template.clone",
            source="templates",
            related_ids={
                "template_id": str(template.id),
                "template_slug": slug,
                "flow_id": str(flow.id),
            },
            actor_user_id=current_user.id,
            outcome="success",
        )
        db.add(event)
    except Exception:
        pass

    await db.commit()

    return wrap_data({
        "flow_id": str(flow.id),
        "flow_name": flow_name,
        "redirect_path": f"/automations/{flow.id}",
        "template_slug": slug,
        "required_integrations": template.required_integrations or [],
        "variables_applied": bool(var_list),
    })
