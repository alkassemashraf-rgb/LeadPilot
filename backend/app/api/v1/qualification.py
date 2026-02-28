"""
Qualification Config API — Mission 20
Workspace-scoped lead qualification questions and statuses.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, QualificationConfig
from app.schemas.envelope import ResponseEnvelope, wrap_data
from app.core.modules import require_module_enabled, MODULE_PROMPT_STUDIO
from app.services.entitlements import require_entitlement

router = APIRouter()

DEFAULT_QUESTIONS = [
    {"id": "full_name", "label": "Full Name", "enabled": True, "order": 0},
    {"id": "company_email", "label": "Company Email", "enabled": True, "order": 1},
    {"id": "budget_range", "label": "Budget Range", "enabled": False, "order": 2},
    {"id": "phone_number", "label": "Phone Number", "enabled": True, "order": 3},
    {"id": "timeline", "label": "Project Timeline", "enabled": False, "order": 4},
    {"id": "company_name", "label": "Company Name", "enabled": False, "order": 5},
]

DEFAULT_STATUSES = [
    {"key": "new", "label": "New", "color": "#94a3b8", "enabled": True},
    {"key": "qualified", "label": "Qualified", "color": "#10b981", "enabled": True},
    {"key": "unqualified", "label": "Unqualified", "color": "#ef4444", "enabled": True},
    {"key": "nurturing", "label": "Nurturing", "color": "#f59e0b", "enabled": True},
]


@router.get("", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "read")), Depends(require_entitlement("prompt_studio"))])
async def get_qualification_config(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Get or lazily create qualification config for workspace."""
    result = await db.execute(
        select(QualificationConfig).where(
            QualificationConfig.workspace_id == workspace.id
        )
    )
    config = result.scalars().first()
    if not config:
        config = QualificationConfig(
            workspace_id=workspace.id,
            qualification_questions=DEFAULT_QUESTIONS,
            qualification_statuses=DEFAULT_STATUSES,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return wrap_data({
        "id": str(config.id),
        "version": config.version,
        "qualification_questions": config.qualification_questions,
        "qualification_statuses": config.qualification_statuses,
    })


@router.post("", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "write")), Depends(require_entitlement("prompt_studio"))])
async def update_qualification_config(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Update qualification questions and/or statuses."""
    result = await db.execute(
        select(QualificationConfig).where(
            QualificationConfig.workspace_id == workspace.id
        )
    )
    config = result.scalars().first()
    if not config:
        config = QualificationConfig(
            workspace_id=workspace.id,
            qualification_questions=DEFAULT_QUESTIONS,
            qualification_statuses=DEFAULT_STATUSES,
        )
        db.add(config)
        await db.flush()

    if "qualification_questions" in body:
        config.qualification_questions = body["qualification_questions"]
    if "qualification_statuses" in body:
        config.qualification_statuses = body["qualification_statuses"]
    config.version += 1

    await db.commit()
    await db.refresh(config)

    return wrap_data({
        "id": str(config.id),
        "version": config.version,
        "qualification_questions": config.qualification_questions,
        "qualification_statuses": config.qualification_statuses,
    })
