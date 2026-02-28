"""
Template Catalog API — Mission 27

Workspace-facing endpoints for browsing and cloning automation templates.
Admin-facing endpoints are in admin.py.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
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
)
from app.schemas.envelope import wrap_data, wrap_error
from app.services.entitlements import require_entitlement

router = APIRouter()


class CloneTemplatePayload(BaseModel):
    name: Optional[str] = None  # Defaults to template name if not provided


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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all active templates with optional filters."""
    query = select(AutomationTemplate).where(AutomationTemplate.is_active == True)

    if category:
        query = query.where(AutomationTemplate.category == category)
    if featured is not None:
        query = query.where(AutomationTemplate.is_featured == featured)

    query = query.order_by(
        AutomationTemplate.is_featured.desc(),
        AutomationTemplate.name.asc()
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    # Platform filter is done in Python since platforms is a JSON array
    if platform:
        templates = [t for t in templates if platform in (t.platforms or [])]

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
        }
        for t in templates
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
    Redirects to canvas builder at /automations/{flow_id}.
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

    # Create new flow in workspace
    flow_name = (payload.name or "").strip() or template.name
    now = datetime.utcnow()

    flow = Flow(
        name=flow_name,
        description=template.description,
        workspace_id=workspace.id,
        status=FlowStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    db.add(flow)
    await db.flush()

    # Create draft from template builder_graph_json
    draft = FlowDraft(
        workspace_id=workspace.id,
        flow_id=flow.id,
        builder_graph_json=latest_version.builder_graph_json,
        updated_by_user_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)

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
    })
