"""
Tests for Mission 14 — Entitlements Service.
Tests the layered enforcement: global toggle → plan → override → usage.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from sqlmodel import select
from app.models.models import (
    Plan, PlanEntitlement, WorkspacePlan,
    WorkspaceEntitlementOverride, UsageMeter,
    SystemModuleConfig, Workspace, User,
)
from app.services.entitlements import (
    check_entitlement, increment_usage, get_workspace_entitlements,
    _current_period, _ensure_workspace_plan,
)
from app.core.modules import module_cache


@pytest.fixture(autouse=True)
def clear_module_cache():
    """Clear the module cache before each test to prevent cross-test bleed."""
    module_cache._cache.clear()
    yield
    module_cache._cache.clear()


@pytest_asyncio.fixture
async def seed_plan_data(db_session):
    """Seed a free plan with entitlements for testing."""
    # Create a workspace
    workspace = Workspace(id=uuid4(), name="Test WS", subscription_tier="free")
    db_session.add(workspace)

    # Create a user
    user = User(
        id=uuid4(), email="test-ent@example.com",
        hashed_password="x", is_active=True,
    )
    db_session.add(user)

    # Create free plan
    free_plan = Plan(
        id=uuid4(), name="free", display_name="Free",
        is_active=True, sort_order=0,
    )
    db_session.add(free_plan)

    # Entitlements: prompt_studio with limit 2, analytics unlimited
    ent_prompt = PlanEntitlement(
        plan_id=free_plan.id, module_key="prompt_studio", hard_limit=2,
    )
    ent_analytics = PlanEntitlement(
        plan_id=free_plan.id, module_key="analytics", hard_limit=None,
    )
    db_session.add(ent_prompt)
    db_session.add(ent_analytics)

    # Assign workspace to free plan
    wp = WorkspacePlan(
        workspace_id=workspace.id, plan_id=free_plan.id,
    )
    db_session.add(wp)

    # Enable modules globally
    for mod_name in ["prompt_studio", "analytics", "runtime_engine"]:
        mod = SystemModuleConfig(module_name=mod_name, is_enabled=True)
        db_session.add(mod)

    await db_session.flush()

    return {
        "workspace": workspace,
        "user": user,
        "free_plan": free_plan,
        "ent_prompt": ent_prompt,
        "ent_analytics": ent_analytics,
    }


@pytest.mark.asyncio
async def test_entitlement_allowed_in_plan(db_session, seed_plan_data):
    """Module in plan + globally enabled → allowed."""
    ws = seed_plan_data["workspace"]
    result = await check_entitlement(ws.id, "prompt_studio", db_session)
    assert result.allowed is True
    assert result.limit == 2
    assert result.used == 0


@pytest.mark.asyncio
async def test_entitlement_unlimited_module(db_session, seed_plan_data):
    """Module with hard_limit=None → unlimited, allowed."""
    ws = seed_plan_data["workspace"]
    result = await check_entitlement(ws.id, "analytics", db_session)
    assert result.allowed is True
    assert result.limit is None


@pytest.mark.asyncio
async def test_entitlement_not_in_plan(db_session, seed_plan_data):
    """Module globally enabled but NOT in plan → blocked."""
    ws = seed_plan_data["workspace"]
    result = await check_entitlement(ws.id, "runtime_engine", db_session)
    assert result.allowed is False
    assert "not included" in result.reason.lower()


@pytest.mark.asyncio
async def test_entitlement_globally_disabled(db_session, seed_plan_data):
    """Module globally disabled → blocked regardless of plan."""
    ws = seed_plan_data["workspace"]
    # Disable prompt_studio globally
    res = await db_session.execute(
        select(SystemModuleConfig).where(SystemModuleConfig.module_name == "prompt_studio")
    )
    mod = res.scalars().first()
    mod.is_enabled = False
    await db_session.flush()

    # Invalidate cache so check_module_enabled re-queries
    module_cache.invalidate("prompt_studio")

    result = await check_entitlement(ws.id, "prompt_studio", db_session)
    assert result.allowed is False
    assert "disabled" in result.reason.lower()


@pytest.mark.asyncio
async def test_usage_limit_reached(db_session, seed_plan_data):
    """Usage at limit → blocked."""
    ws = seed_plan_data["workspace"]
    period = _current_period()

    # Set usage to limit (2)
    meter = UsageMeter(
        workspace_id=ws.id, module_key="prompt_studio",
        period=period, counter=2,
    )
    db_session.add(meter)
    await db_session.flush()

    result = await check_entitlement(ws.id, "prompt_studio", db_session)
    assert result.allowed is False
    assert "limit reached" in result.reason.lower()
    assert result.used == 2
    assert result.limit == 2


@pytest.mark.asyncio
async def test_override_increases_limit(db_session, seed_plan_data):
    """Admin override increases limit → allowed even at plan limit."""
    ws = seed_plan_data["workspace"]
    period = _current_period()

    # Usage at 2 (plan limit)
    meter = UsageMeter(
        workspace_id=ws.id, module_key="prompt_studio",
        period=period, counter=2,
    )
    db_session.add(meter)

    # Override raises limit to 10
    override = WorkspaceEntitlementOverride(
        workspace_id=ws.id, module_key="prompt_studio", hard_limit=10,
    )
    db_session.add(override)
    await db_session.flush()

    result = await check_entitlement(ws.id, "prompt_studio", db_session)
    assert result.allowed is True
    assert result.limit == 10
    assert result.used == 2


@pytest.mark.asyncio
async def test_increment_usage(db_session, seed_plan_data):
    """increment_usage creates/updates UsageMeter."""
    ws = seed_plan_data["workspace"]

    val1 = await increment_usage(ws.id, "prompt_studio", db_session)
    assert val1 == 1

    val2 = await increment_usage(ws.id, "prompt_studio", db_session)
    assert val2 == 2


@pytest.mark.asyncio
async def test_get_workspace_entitlements(db_session, seed_plan_data):
    """get_workspace_entitlements returns merged data."""
    ws = seed_plan_data["workspace"]
    ents = await get_workspace_entitlements(ws.id, db_session)
    assert len(ents) == 2

    prompt_ent = next(e for e in ents if e["module_key"] == "prompt_studio")
    assert prompt_ent["plan_limit"] == 2
    assert prompt_ent["plan_name"] == "Free"


@pytest.mark.asyncio
async def test_auto_assign_free_plan(db_session, seed_plan_data):
    """Workspace without plan gets auto-assigned to free."""
    new_ws = Workspace(id=uuid4(), name="New WS")
    db_session.add(new_ws)
    await db_session.flush()

    wp = await _ensure_workspace_plan(new_ws.id, db_session)
    assert wp is not None
    assert wp.plan_id == seed_plan_data["free_plan"].id
