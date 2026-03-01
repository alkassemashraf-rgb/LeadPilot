"""
Mission 28: Settings Pages API Tests
Tests GET /settings/profile, PATCH /settings/profile,
GET /settings/subscription, GET /settings/modules.
"""
import pytest
import pytest_asyncio
from typing import Optional
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Plan, PlanEntitlement, WorkspacePlan,
    SystemModuleConfig, Workspace, WorkspaceMember,
)
from app.core.modules import module_cache


# ── Helpers ─────────────────────────────────────────────────────────


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Settings User",
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
async def settings_setup(async_client: AsyncClient, db_session: AsyncSession):
    """Create user + workspace + plan for settings tests."""
    token = await _signup_and_login(async_client, "settings_test@example.com")

    ws = Workspace(id=uuid4(), name="Settings WS", subscription_tier="free")
    db_session.add(ws)

    me_res = await async_client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = UUID(me_res.json()["data"]["id"])

    member = WorkspaceMember(user_id=user_id, workspace_id=ws.id, role="owner")
    db_session.add(member)

    plan = Plan(
        id=uuid4(), name="pro", display_name="Professional",
        is_active=True, sort_order=2, description="Pro plan",
    )
    db_session.add(plan)

    ent = PlanEntitlement(plan_id=plan.id, module_key="analytics", hard_limit=500)
    db_session.add(ent)

    wp = WorkspacePlan(workspace_id=ws.id, plan_id=plan.id)
    db_session.add(wp)

    for mod_name in ["analytics", "prompt_studio"]:
        mod = SystemModuleConfig(module_name=mod_name, is_enabled=True)
        db_session.add(mod)

    await db_session.flush()

    return {"token": token, "workspace": ws, "plan": plan}


# ── Profile Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile(async_client: AsyncClient, settings_setup):
    setup = settings_setup
    headers = _auth(setup["token"])

    response = await async_client.get("/api/v1/settings/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "settings_test@example.com"
    assert data["data"]["full_name"] == "Settings User"


@pytest.mark.asyncio
async def test_patch_profile_updates_full_name(async_client: AsyncClient, settings_setup):
    setup = settings_setup
    headers = _auth(setup["token"])

    response = await async_client.patch(
        "/api/v1/settings/profile",
        json={"full_name": "Updated Settings User"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == "Updated Settings User"


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/settings/profile")
    assert response.status_code in (401, 403)


# ── Subscription Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_subscription(async_client: AsyncClient, settings_setup):
    setup = settings_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.get("/api/v1/settings/subscription", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["plan"] is not None
    assert data["data"]["plan"]["display_name"] == "Professional"
    assert "usage" in data["data"]


# ── Modules Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_modules(async_client: AsyncClient, settings_setup):
    setup = settings_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.get("/api/v1/settings/modules", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    for mod in data["data"]:
        assert "module_key" in mod
        assert "label" in mod
        assert "enabled" in mod
        assert "source" in mod
