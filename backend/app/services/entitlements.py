"""
Entitlement service for Mission 14 — Commercial Plans & Usage Enforcement.

Layered enforcement:
  0. Plan override (PlanOverride) — time-bound plan grant (Mission 34)
  1. Global module toggle (SystemModuleConfig) — kill switch
  2. Plan entitlement (PlanEntitlement) — is the module in the workspace's plan?
  3. Workspace override (WorkspaceEntitlementOverride) — admin override on limit
  4. Usage meter (UsageMeter) — has the workspace exceeded its monthly limit?
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.core.modules import check_module_enabled
from app.models.models import (
    Plan,
    PlanEntitlement,
    PlanOverride,
    WorkspacePlan,
    WorkspaceEntitlementOverride,
    UsageMeter,
)

logger = logging.getLogger(__name__)


@dataclass
class EntitlementResult:
    allowed: bool
    reason: str
    limit: Optional[int] = None
    used: int = 0


def _current_period() -> str:
    """Return the current billing period as YYYY-MM."""
    return datetime.utcnow().strftime("%Y-%m")


async def _ensure_workspace_plan(workspace_id: UUID, db: AsyncSession) -> Optional[WorkspacePlan]:
    """Get or auto-assign the free plan if none exists."""
    result = await db.execute(
        select(WorkspacePlan).where(WorkspacePlan.workspace_id == workspace_id)
    )
    wp = result.scalars().first()
    if wp:
        return wp

    # Auto-assign the free plan
    plan_result = await db.execute(select(Plan).where(Plan.name == "free"))
    free_plan = plan_result.scalars().first()
    if not free_plan:
        logger.warning("[entitlements] No 'free' plan found — cannot auto-assign.")
        return None

    wp = WorkspacePlan(
        workspace_id=workspace_id,
        plan_id=free_plan.id,
    )
    db.add(wp)
    await db.flush()
    return wp


async def _get_effective_plan(
    workspace_id: UUID,
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> Tuple[Optional[UUID], str, Optional[datetime]]:
    """
    Return (plan_id, source, override_expires_at) for a workspace.

    Precedence:
      1. Active PlanOverride within time window → source="override"
      2. WorkspacePlan (base, auto-assigns free) → source="base"
      3. No plan at all → source="free", plan_id=None

    Self-heals stale ACTIVE overrides where ends_at <= now.
    """
    now = now or datetime.utcnow()

    result = await db.execute(
        select(PlanOverride)
        .where(
            PlanOverride.workspace_id == workspace_id,
            PlanOverride.status == "active",
        )
        .order_by(PlanOverride.created_at.desc())
    )
    override = result.scalars().first()

    if override:
        if override.ends_at <= now:
            # Self-heal: Celery worker hasn't fired yet
            override.status = "expired"
            await db.flush()
            logger.info(
                f"[entitlements] Self-healed stale PlanOverride {override.id} for workspace {workspace_id}"
            )
        else:
            return override.plan_id, "override", override.ends_at

    # Fall back to permanent base plan
    wp = await _ensure_workspace_plan(workspace_id, db)
    if not wp:
        return None, "free", None
    return wp.plan_id, "base", None


async def check_entitlement(
    workspace_id: UUID,
    module_key: str,
    db: AsyncSession,
) -> EntitlementResult:
    """
    Full layered entitlement check.
    Returns EntitlementResult with allowed=True/False and context.
    """
    # Layer 1: Global toggle
    global_enabled = await check_module_enabled(module_key, db)
    if not global_enabled:
        return EntitlementResult(
            allowed=False,
            reason=f"Module '{module_key}' is globally disabled.",
        )

    # Layer 2: Get effective plan (override > base)
    plan_id, _source, _expires_at = await _get_effective_plan(workspace_id, db)
    if not plan_id:
        # No plan and couldn't auto-assign — allow (graceful fallback)
        return EntitlementResult(allowed=True, reason="No plan configured; defaulting to allow.")

    ent_result = await db.execute(
        select(PlanEntitlement).where(
            PlanEntitlement.plan_id == plan_id,
            PlanEntitlement.module_key == module_key,
        )
    )
    entitlement = ent_result.scalars().first()

    # Layer 3: Check for workspace override (enabled flag + limit)
    override_result = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == workspace_id,
            WorkspaceEntitlementOverride.module_key == module_key,
        )
    )
    override = override_result.scalars().first()

    # If override explicitly disables the module, block
    if override and override.enabled is False:
        return EntitlementResult(
            allowed=False,
            reason=f"Module '{module_key}' is disabled for this workspace by admin override.",
        )

    # If override explicitly enables the module, skip plan check
    if override and override.enabled is True:
        effective_limit = override.hard_limit
    elif not entitlement:
        return EntitlementResult(
            allowed=False,
            reason=f"Module '{module_key}' is not included in your current plan.",
        )
    else:
        effective_limit = override.hard_limit if override else entitlement.hard_limit

    # If limit is None, module is unlimited — allow
    if effective_limit is None:
        return EntitlementResult(allowed=True, reason="Unlimited.", limit=None, used=0)

    # Layer 4: Check usage meter
    period = _current_period()
    usage_result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.workspace_id == workspace_id,
            UsageMeter.module_key == module_key,
            UsageMeter.period == period,
        )
    )
    usage = usage_result.scalars().first()
    current_usage = usage.counter if usage else 0

    if current_usage >= effective_limit:
        return EntitlementResult(
            allowed=False,
            reason=f"Usage limit reached for '{module_key}': {current_usage}/{effective_limit} this month.",
            limit=effective_limit,
            used=current_usage,
        )

    return EntitlementResult(
        allowed=True,
        reason="OK",
        limit=effective_limit,
        used=current_usage,
    )


async def increment_usage(
    workspace_id: UUID,
    module_key: str,
    db: AsyncSession,
) -> int:
    """
    Increment the usage counter for a workspace module in the current period.
    Returns the new counter value.
    """
    period = _current_period()

    result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.workspace_id == workspace_id,
            UsageMeter.module_key == module_key,
            UsageMeter.period == period,
        )
    )
    meter = result.scalars().first()

    if meter:
        meter.counter += 1
        new_val = meter.counter
    else:
        meter = UsageMeter(
            workspace_id=workspace_id,
            module_key=module_key,
            period=period,
            counter=1,
        )
        db.add(meter)
        new_val = 1

    await db.flush()
    return new_val


async def get_workspace_entitlements(
    workspace_id: UUID,
    db: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    Return merged entitlements + usage for a workspace.
    Used by the client-side banner and admin workspace detail.
    """
    plan_id, _source, _expires_at = await _get_effective_plan(workspace_id, db)
    if not plan_id:
        return []

    # Get plan info
    plan = await db.get(Plan, plan_id)
    plan_name = plan.display_name if plan else "Unknown"

    # Get all entitlements for the plan
    ent_result = await db.execute(
        select(PlanEntitlement).where(PlanEntitlement.plan_id == plan_id)
    )
    entitlements = ent_result.scalars().all()

    # Get overrides for this workspace
    override_result = await db.execute(
        select(WorkspaceEntitlementOverride).where(
            WorkspaceEntitlementOverride.workspace_id == workspace_id
        )
    )
    overrides = {o.module_key: o for o in override_result.scalars().all()}

    # Get usage for current period
    period = _current_period()
    usage_result = await db.execute(
        select(UsageMeter).where(
            UsageMeter.workspace_id == workspace_id,
            UsageMeter.period == period,
        )
    )
    usage_map = {u.module_key: u.counter for u in usage_result.scalars().all()}

    output = []
    for ent in entitlements:
        override = overrides.get(ent.module_key)
        effective_limit = override.hard_limit if override and override.hard_limit is not None else ent.hard_limit
        output.append({
            "module_key": ent.module_key,
            "plan_limit": ent.hard_limit,
            "effective_limit": effective_limit,
            "has_override": ent.module_key in overrides,
            "used": usage_map.get(ent.module_key, 0),
            "plan_name": plan_name,
        })

    return output


# --- FastAPI Dependency Factory ---

def require_entitlement(module_key: str, action: str = "execute", increment: bool = False):
    """
    FastAPI dependency factory for entitlement enforcement.

    Checks global toggle + plan entitlement + usage limits.
    If increment=True, also bumps the usage counter on success.

    Usage:
        @router.post("/run", dependencies=[Depends(require_entitlement("dispatch_engine", increment=True))])
    """
    async def _dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        x_workspace_id: Optional[UUID] = Header(None, alias="X-Workspace-ID"),
    ):
        if not x_workspace_id:
            # No workspace context — skip entitlement check (non-workspace routes)
            return

        result = await check_entitlement(x_workspace_id, module_key, db)
        if not result.allowed:
            raise HTTPException(
                status_code=403,
                detail=f"ENTITLEMENT_BLOCKED: {result.reason}",
            )

        if increment:
            await increment_usage(x_workspace_id, module_key, db)

    return _dependency
