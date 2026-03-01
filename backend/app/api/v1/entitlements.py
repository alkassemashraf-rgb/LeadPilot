"""
Entitlements Router — Mission 28
Product-facing endpoint: returns effective tier + modules + usage for the active workspace.
"""
from typing import Any

from fastapi import APIRouter, Depends
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


@router.get("")
async def get_entitlements(
    workspace: Workspace = Depends(get_active_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return the effective entitlements for the active workspace.
    Includes plan info, module availability, and usage metrics.
    """
    wp = await _ensure_workspace_plan(workspace.id, db)

    # Plan info
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

    # Get plan entitlements (module_key list in the plan)
    plan_module_keys: set[str] = set()
    if wp:
        ent_result = await db.execute(
            select(PlanEntitlement).where(PlanEntitlement.plan_id == wp.plan_id)
        )
        plan_module_keys = {e.module_key for e in ent_result.scalars().all()}

    # Get workspace overrides
    override_result = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == workspace.id
        )
    )
    overrides = {o.module_key: o for o in override_result.scalars().all()}

    # Get global module states
    global_result = await db.execute(select(SystemModuleConfig))
    global_states = {m.module_name: m.is_enabled for m in global_result.scalars().all()}

    # Build modules list
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

    # Usage data (reuse existing service)
    usage = await get_workspace_entitlements(workspace.id, db)

    await db.commit()

    return wrap_data({
        "plan": plan_info,
        "modules": modules,
        "usage": usage,
    })
