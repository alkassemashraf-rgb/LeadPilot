"""
Qualification Criteria API — Mission 29
Workspace-scoped dynamic lead qualification criteria (stored as rows).
"""
import re
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, QualificationCriterion
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.modules import require_module_enabled, MODULE_PROMPT_STUDIO
from app.services.entitlements import require_entitlement

router = APIRouter()

VALID_CRITERION_TYPES = {"boolean", "enum", "text", "score"}


def _slugify(label: str) -> str:
    """Convert label to a snake_case code."""
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "criterion"


# --- Schemas ---


class CriterionCreate(BaseModel):
    label: str
    code: Optional[str] = None
    description: Optional[str] = None
    criterion_type: str = "boolean"
    enum_values: Optional[List[str]] = None
    weight: Optional[int] = None
    sort_order: int = 0
    is_enabled: bool = True


class CriterionUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    criterion_type: Optional[str] = None
    enum_values: Optional[List[str]] = None
    weight: Optional[int] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None


def _criterion_to_dict(c: QualificationCriterion) -> dict:
    return {
        "id": str(c.id),
        "code": c.code,
        "label": c.label,
        "description": c.description,
        "criterion_type": c.criterion_type,
        "enum_values": c.enum_values,
        "weight": c.weight,
        "sort_order": c.sort_order,
        "is_enabled": c.is_enabled,
        "created_at": c.created_at.isoformat(),
    }


# --- Endpoints ---


@router.get(
    "/qualification",
    response_model=ResponseEnvelope[List[dict]],
    dependencies=[
        Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "read")),
        Depends(require_entitlement("prompt_studio")),
    ],
)
async def list_criteria(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """List all qualification criteria for the active workspace."""
    result = await db.execute(
        select(QualificationCriterion)
        .where(QualificationCriterion.workspace_id == workspace.id)
        .order_by(QualificationCriterion.sort_order)
    )
    criteria = result.scalars().all()
    return wrap_data([_criterion_to_dict(c) for c in criteria])


@router.post(
    "/qualification",
    response_model=ResponseEnvelope[dict],
    dependencies=[
        Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "write")),
        Depends(require_entitlement("prompt_studio")),
    ],
)
async def create_criterion(
    body: CriterionCreate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Create a new qualification criterion."""
    if not body.label or not body.label.strip():
        return wrap_error("Label is required")

    if body.criterion_type not in VALID_CRITERION_TYPES:
        return wrap_error(f"Invalid criterion_type. Must be one of: {', '.join(VALID_CRITERION_TYPES)}")

    code = body.code or _slugify(body.label)

    # Check uniqueness within workspace
    existing = await db.execute(
        select(QualificationCriterion).where(
            QualificationCriterion.workspace_id == workspace.id,
            QualificationCriterion.code == code,
        )
    )
    if existing.scalars().first():
        return wrap_error(f"A criterion with code '{code}' already exists in this workspace")

    criterion = QualificationCriterion(
        workspace_id=workspace.id,
        code=code,
        label=body.label.strip(),
        description=body.description,
        criterion_type=body.criterion_type,
        enum_values=body.enum_values,
        weight=body.weight,
        sort_order=body.sort_order,
        is_enabled=body.is_enabled,
    )
    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)

    return wrap_data(_criterion_to_dict(criterion))


@router.patch(
    "/qualification/{criterion_id}",
    response_model=ResponseEnvelope[dict],
    dependencies=[
        Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "write")),
        Depends(require_entitlement("prompt_studio")),
    ],
)
async def update_criterion(
    criterion_id: UUID,
    body: CriterionUpdate,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Update a qualification criterion."""
    result = await db.execute(
        select(QualificationCriterion).where(
            QualificationCriterion.id == criterion_id,
            QualificationCriterion.workspace_id == workspace.id,
        )
    )
    criterion = result.scalars().first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    if body.label is not None:
        criterion.label = body.label.strip()
    if body.description is not None:
        criterion.description = body.description
    if body.criterion_type is not None:
        if body.criterion_type not in VALID_CRITERION_TYPES:
            return wrap_error(f"Invalid criterion_type. Must be one of: {', '.join(VALID_CRITERION_TYPES)}")
        criterion.criterion_type = body.criterion_type
    if body.enum_values is not None:
        criterion.enum_values = body.enum_values
    if body.weight is not None:
        criterion.weight = body.weight
    if body.sort_order is not None:
        criterion.sort_order = body.sort_order
    if body.is_enabled is not None:
        criterion.is_enabled = body.is_enabled

    await db.commit()
    await db.refresh(criterion)

    return wrap_data(_criterion_to_dict(criterion))


@router.delete(
    "/qualification/{criterion_id}",
    response_model=ResponseEnvelope[dict],
    dependencies=[
        Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "write")),
        Depends(require_entitlement("prompt_studio")),
    ],
)
async def delete_criterion(
    criterion_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Delete a qualification criterion."""
    result = await db.execute(
        select(QualificationCriterion).where(
            QualificationCriterion.id == criterion_id,
            QualificationCriterion.workspace_id == workspace.id,
        )
    )
    criterion = result.scalars().first()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    await db.delete(criterion)
    await db.commit()

    return wrap_data({"deleted": True})
