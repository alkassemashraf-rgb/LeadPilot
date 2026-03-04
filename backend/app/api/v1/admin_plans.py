"""
Admin Plan Override API — Mission 34
Endpoints for super-admins to grant time-bound plan overrides to workspaces.
All endpoints require is_superuser.
"""
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.api.deps import get_current_user
from app.models.models import Plan, PlanOverride, Workspace, User
from app.schemas.envelope import wrap_data, wrap_error
from app.services.audit_service import audit_event
from app.services.entitlements import _get_effective_plan, _ensure_workspace_plan

router = APIRouter()

MAX_OVERRIDE_DAYS = 365


async def require_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin privileges required")
    return current_user


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateOverrideRequest(BaseModel):
    plan_id: UUID
    duration_days: Optional[int] = None
    ends_at: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def check_duration_or_ends_at(self) -> "CreateOverrideRequest":
        if self.duration_days is None and self.ends_at is None:
            raise ValueError("Provide either duration_days or ends_at")
        if self.duration_days is not None and self.duration_days <= 0:
            raise ValueError("duration_days must be > 0")
        if self.duration_days is not None and self.duration_days > MAX_OVERRIDE_DAYS:
            raise ValueError(f"duration_days cannot exceed {MAX_OVERRIDE_DAYS}")
        return self


class RevokeOverrideRequest(BaseModel):
    reason: Optional[str] = None


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _effective_plan_summary(workspace_id: UUID, db: AsyncSession) -> dict:
    plan_id, source, expires_at = await _get_effective_plan(workspace_id, db)
    plan_name = None
    plan_display = None
    if plan_id:
        plan = await db.get(Plan, plan_id)
        if plan:
            plan_name = plan.name
            plan_display = plan.display_name
    return {
        "plan_code": plan_name,
        "plan_display_name": plan_display,
        "plan_source": source,
        "override_expires_at": expires_at.isoformat() if expires_at else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/workspaces/{workspace_id}/plan-status", response_model=None)
async def get_workspace_plan_status(
    workspace_id: UUID,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return the base plan, active plan override (if any), and effective plan for a workspace.
    """
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        return wrap_error("Workspace not found")

    # Base plan
    wp = await _ensure_workspace_plan(workspace_id, db)
    base_plan = None
    if wp:
        plan = await db.get(Plan, wp.plan_id)
        if plan:
            base_plan = {"id": str(plan.id), "code": plan.name, "display_name": plan.display_name}

    # Active override
    result = await db.execute(
        select(PlanOverride)
        .where(PlanOverride.workspace_id == workspace_id, PlanOverride.status == "active")
        .order_by(PlanOverride.created_at.desc())
    )
    active_override = result.scalars().first()
    override_data = None
    if active_override:
        now = datetime.utcnow()
        if active_override.ends_at > now:
            override_plan = await db.get(Plan, active_override.plan_id)
            override_data = {
                "id": str(active_override.id),
                "plan_code": override_plan.name if override_plan else None,
                "plan_display_name": override_plan.display_name if override_plan else None,
                "starts_at": active_override.starts_at.isoformat(),
                "ends_at": active_override.ends_at.isoformat(),
                "reason": active_override.reason,
                "created_by_admin_id": str(active_override.created_by_admin_id),
            }

    effective = await _effective_plan_summary(workspace_id, db)
    await db.commit()

    return wrap_data({
        "workspace_id": str(workspace_id),
        "base_plan": base_plan,
        "active_override": override_data,
        "effective": effective,
    })


@router.post("/workspaces/{workspace_id}/plan-override", response_model=None)
async def create_workspace_plan_override(
    workspace_id: UUID,
    body: CreateOverrideRequest,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Grant a time-bound plan override to a workspace. Blocks if an override is already active.
    """
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        return wrap_error("Workspace not found")

    # Validate plan exists
    plan = await db.get(Plan, body.plan_id)
    if not plan:
        return wrap_error("Plan not found")

    # Check for existing active override
    now = datetime.utcnow()
    existing_result = await db.execute(
        select(PlanOverride).where(
            PlanOverride.workspace_id == workspace_id,
            PlanOverride.status == "active",
        )
    )
    existing = existing_result.scalars().first()
    if existing and existing.ends_at > now:
        return wrap_error(
            f"Workspace already has an active plan override (expires {existing.ends_at.isoformat()}). "
            "Revoke it first before creating a new one."
        )

    # Resolve starts_at / ends_at
    starts_at = body.starts_at or now
    if body.ends_at:
        ends_at = body.ends_at
    else:
        ends_at = starts_at + timedelta(days=body.duration_days)  # type: ignore[arg-type]

    # Normalize to naive UTC (strip timezone info if provided as aware datetime)
    if starts_at.tzinfo is not None:
        starts_at = starts_at.replace(tzinfo=None)
    if ends_at.tzinfo is not None:
        ends_at = ends_at.replace(tzinfo=None)

    if ends_at <= starts_at:
        return wrap_error("ends_at must be after starts_at")

    override = PlanOverride(
        workspace_id=workspace_id,
        plan_id=body.plan_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=body.reason,
        status="active",
        created_by_admin_id=admin.id,
    )
    db.add(override)
    await db.flush()

    # Audit log
    await audit_event(
        db=db,
        action="PLAN_OVERRIDE_CREATED",
        entity_type="plan_override",
        entity_id=str(override.id),
        actor_user_id=admin.id,
        workspace_id=workspace_id,
        outcome="success",
        metadata={
            "plan_code": plan.name,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "reason": body.reason,
        },
    )

    effective = await _effective_plan_summary(workspace_id, db)
    await db.commit()

    return wrap_data({
        "override": {
            "id": str(override.id),
            "plan_code": plan.name,
            "starts_at": override.starts_at.isoformat(),
            "ends_at": override.ends_at.isoformat(),
            "reason": override.reason,
        },
        "effective": effective,
    })


@router.post("/workspaces/{workspace_id}/plan-override/revoke", response_model=None)
async def revoke_workspace_plan_override(
    workspace_id: UUID,
    body: RevokeOverrideRequest,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Revoke the active plan override for a workspace. Reverts to base plan immediately.
    """
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        return wrap_error("Workspace not found")

    now = datetime.utcnow()
    result = await db.execute(
        select(PlanOverride).where(
            PlanOverride.workspace_id == workspace_id,
            PlanOverride.status == "active",
        )
    )
    override = result.scalars().first()
    if not override or override.ends_at <= now:
        return wrap_error("No active plan override found for this workspace")

    override.status = "revoked"
    override.revoked_at = now
    override.revoked_by_admin_id = admin.id
    await db.flush()

    # Audit log
    await audit_event(
        db=db,
        action="PLAN_OVERRIDE_REVOKED",
        entity_type="plan_override",
        entity_id=str(override.id),
        actor_user_id=admin.id,
        workspace_id=workspace_id,
        outcome="success",
        metadata={"reason": body.reason},
    )

    effective = await _effective_plan_summary(workspace_id, db)
    await db.commit()

    return wrap_data({"effective": effective})
