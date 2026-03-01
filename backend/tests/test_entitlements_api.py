"""
Mission 28: Entitlements API Tests
Tests GET /api/v1/entitlements returns plan + modules + usage for the active workspace.
"""
import pytest
import pytest_asyncio
from typing import Optional
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Plan, PlanEntitlement, WorkspacePlan,
    WorkspaceEntitlementOverride, SystemModuleConfig,
    Workspace, WorkspaceMember,
)
from app.core.modules import module_cache


# ── Helpers ─────────────────────────────────────────────────────────


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Test User",
    })
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepassword123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    return login.json()["data"]["access_token"]


def _auth(token: str, workspace_id: Optional[str] = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-ID"] = workspace_id
    return headers


@pytest.fixture(autouse=True)
def clear_module_cache():
    module_cache._cache.clear()
    yield
    module_cache._cache.clear()


@pytest_asyncio.fixture
async def entitlement_setup(async_client: AsyncClient, db_session: AsyncSession):
    """Create a user + workspace + plan with entitlements."""
    token = await _signup_and_login(async_client, "entapi@example.com")

    # Create workspace
    ws = Workspace(id=uuid4(), name="EntAPI WS", subscription_tier="free")
    db_session.add(ws)

    # Get user from auth/me
    me_res = await async_client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = UUID(me_res.json()["data"]["id"])

    # Add user as workspace member
    member = WorkspaceMember(
        user_id=user_id, workspace_id=ws.id, role="owner",
    )
    db_session.add(member)

    # Create plan
    plan = Plan(
        id=uuid4(), name="starter", display_name="Starter",
        is_active=True, sort_order=1, description="Starter plan",
    )
    db_session.add(plan)

    # Add entitlements to plan
    ent1 = PlanEntitlement(plan_id=plan.id, module_key="prompt_studio", hard_limit=50)
    ent2 = PlanEntitlement(plan_id=plan.id, module_key="analytics", hard_limit=None)
    db_session.add_all([ent1, ent2])

    # Assign plan to workspace
    wp = WorkspacePlan(workspace_id=ws.id, plan_id=plan.id)
    db_session.add(wp)

    # Enable modules globally
    for mod_name in ["prompt_studio", "analytics", "zoho_sync"]:
        mod = SystemModuleConfig(module_name=mod_name, is_enabled=True)
        db_session.add(mod)

    await db_session.flush()

    return {
        "token": token,
        "workspace": ws,
        "plan": plan,
    }


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entitlements_returns_plan_info(async_client: AsyncClient, entitlement_setup):
    setup = entitlement_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.get("/api/v1/entitlements", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["plan"] is not None
    assert data["data"]["plan"]["code"] == "starter"
    assert data["data"]["plan"]["display_name"] == "Starter"


@pytest.mark.asyncio
async def test_entitlements_returns_modules(async_client: AsyncClient, entitlement_setup):
    setup = entitlement_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.get("/api/v1/entitlements", headers=headers)
    data = response.json()["data"]
    assert "modules" in data
    assert isinstance(data["modules"], list)
    assert len(data["modules"]) > 0

    # Check each module has expected fields
    for mod in data["modules"]:
        assert "module_key" in mod
        assert "enabled" in mod
        assert "source" in mod


@pytest.mark.asyncio
async def test_entitlements_returns_usage(async_client: AsyncClient, entitlement_setup):
    setup = entitlement_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.get("/api/v1/entitlements", headers=headers)
    data = response.json()["data"]
    assert "usage" in data
    assert isinstance(data["usage"], list)

    # prompt_studio should appear with limit 50
    ps_usage = next((u for u in data["usage"] if u["module_key"] == "prompt_studio"), None)
    assert ps_usage is not None
    assert ps_usage["plan_limit"] == 50


@pytest.mark.asyncio
async def test_entitlements_module_override_reflected(
    async_client: AsyncClient, entitlement_setup, db_session: AsyncSession,
):
    setup = entitlement_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    # Add override to enable zoho_sync (not in plan entitlements)
    override = WorkspaceEntitlementOverride(
        workspace_id=setup["workspace"].id,
        module_key="zoho_sync",
        enabled=True,
    )
    db_session.add(override)
    await db_session.flush()

    response = await async_client.get("/api/v1/entitlements", headers=headers)
    data = response.json()["data"]

    zoho_mod = next((m for m in data["modules"] if m["module_key"] == "zoho_sync"), None)
    assert zoho_mod is not None
    assert zoho_mod["enabled"] is True
    assert zoho_mod["source"] == "override"


@pytest.mark.asyncio
async def test_entitlements_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/entitlements")
    assert response.status_code in (401, 403)
