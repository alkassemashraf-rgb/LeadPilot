"""
Settings Profile Router — Mission 28
User profile, subscription (read-only), and modules (read-only) endpoints.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.core.modules import ALL_MODULES
from app.core.catalog_registry import MODULE_LABELS
from app.api.deps import get_current_user, get_active_workspace
from app.models.models import (
    User,
    Workspace,
    Plan,
    PlanEntitlement,
    WorkspaceEntitlementOverride,
    SystemModuleConfig,
)
from app.schemas.envelope import wrap_data
from app.services.entitlements import get_workspace_entitlements, _ensure_workspace_plan

router = APIRouter()


# ── Profile ──────────────────────────────────────────────────────────


class PatchProfileRequest(BaseModel):
    full_name: Optional[str] = None


@router.get("/profile")
async def get_profile(
    user: User = Depends(get_current_user),
) -> Any:
    """Return current user's profile information."""
    return wrap_data({
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    })


@router.patch("/profile")
async def update_profile(
    payload: PatchProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update current user's profile (currently only full_name)."""
    if payload.full_name is not None:
        user.full_name = payload.full_name

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return wrap_data({
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    })


# ── Subscription (read-only) ────────────────────────────────────────


@router.get("/subscription")
async def get_subscription(
    workspace: Workspace = Depends(get_active_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Read-only subscription info for the active workspace."""
    wp = await _ensure_workspace_plan(workspace.id, db)

    plan_info = None
    if wp:
        plan = await db.get(Plan, wp.plan_id)
        if plan:
            plan_info = {
                "id": str(plan.id),
                "code": plan.name,
                "display_name": plan.display_name,
                "description": plan.description,
            }

    usage = await get_workspace_entitlements(workspace.id, db)
    await db.commit()

    return wrap_data({
        "plan": plan_info,
        "assigned_at": wp.assigned_at.isoformat() if wp and wp.assigned_at else None,
        "usage": usage,
    })


# ── Modules (read-only) ─────────────────────────────────────────────


@router.get("/modules")
async def get_effective_modules(
    workspace: Workspace = Depends(get_active_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Read-only list of effective module availability for the active workspace."""
    wp = await _ensure_workspace_plan(workspace.id, db)

    # Plan entitlements
    plan_module_keys: set[str] = set()
    if wp:
        ent_result = await db.execute(
            select(PlanEntitlement).where(PlanEntitlement.plan_id == wp.plan_id)
        )
        plan_module_keys = {e.module_key for e in ent_result.scalars().all()}

    # Workspace overrides
    override_result = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == workspace.id
        )
    )
    overrides = {o.module_key: o for o in override_result.scalars().all()}

    # Global module states
    global_result = await db.execute(select(SystemModuleConfig))
    global_states = {m.module_name: m.is_enabled for m in global_result.scalars().all()}

    modules = []
    for module_key in sorted(ALL_MODULES):
        globally_enabled = global_states.get(module_key, True)
        override = overrides.get(module_key)

        if not globally_enabled:
            enabled = False
            source = "global_disabled"
        elif override and override.enabled is not None:
            enabled = override.enabled
            source = "override"
        elif module_key in plan_module_keys:
            enabled = True
            source = "plan"
        else:
            enabled = False
            source = "plan"

        modules.append({
            "module_key": module_key,
            "label": MODULE_LABELS.get(module_key, module_key),
            "enabled": enabled,
            "source": source,
        })

    await db.commit()
    return wrap_data(modules)
