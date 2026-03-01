"""
Mission 29: Qualification Criteria Tests
Tests CRUD operations for dynamic lead qualification criteria.
"""
import pytest
import pytest_asyncio
from typing import Optional
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Workspace, WorkspaceMember, SystemModuleConfig,
)
from app.core.modules import module_cache


# ── Helpers ─────────────────────────────────────────────────────────


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Criteria User",
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
async def criteria_setup(async_client: AsyncClient, db_session: AsyncSession):
    """Create user + workspace + modules for criteria tests."""
    token = await _signup_and_login(async_client, "criteria@example.com")

    ws = Workspace(id=uuid4(), name="Criteria WS", subscription_tier="free")
    db_session.add(ws)

    me_res = await async_client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = UUID(me_res.json()["data"]["id"])

    member = WorkspaceMember(user_id=user_id, workspace_id=ws.id, role="owner")
    db_session.add(member)

    db_session.add(SystemModuleConfig(module_name="prompt_studio", is_enabled=True))
    await db_session.flush()

    return {"token": token, "workspace": ws}


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_criterion(async_client: AsyncClient, criteria_setup):
    setup = criteria_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    response = await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Budget Above $10K",
        "description": "Lead has stated budget exceeding $10,000",
        "criterion_type": "boolean",
    }, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["label"] == "Budget Above $10K"
    assert data["data"]["code"] == "budget_above_10k"
    assert data["data"]["criterion_type"] == "boolean"
    assert data["data"]["is_enabled"] is True


@pytest.mark.asyncio
async def test_list_criteria(async_client: AsyncClient, criteria_setup):
    setup = criteria_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    # Create two criteria
    await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Decision Maker",
        "criterion_type": "boolean",
        "sort_order": 0,
    }, headers=headers)

    await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Company Size",
        "criterion_type": "enum",
        "enum_values": ["1-10", "11-50", "51-200", "200+"],
        "sort_order": 1,
    }, headers=headers)

    response = await async_client.get("/api/v1/prompt-studio/qualification", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 2

    # Check enum values preserved
    enum_item = next((c for c in data["data"] if c["code"] == "company_size"), None)
    assert enum_item is not None
    assert enum_item["enum_values"] == ["1-10", "11-50", "51-200", "200+"]


@pytest.mark.asyncio
async def test_update_criterion(async_client: AsyncClient, criteria_setup):
    setup = criteria_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    # Create
    create_res = await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Timeline Under 3 Months",
        "criterion_type": "boolean",
    }, headers=headers)
    criterion_id = create_res.json()["data"]["id"]

    # Update
    response = await async_client.patch(
        f"/api/v1/prompt-studio/qualification/{criterion_id}",
        json={"description": "Project timeline is less than 3 months", "weight": 5},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["description"] == "Project timeline is less than 3 months"
    assert data["data"]["weight"] == 5


@pytest.mark.asyncio
async def test_delete_criterion(async_client: AsyncClient, criteria_setup):
    setup = criteria_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    # Create
    create_res = await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "To Delete",
        "criterion_type": "text",
    }, headers=headers)
    criterion_id = create_res.json()["data"]["id"]

    # Delete
    response = await async_client.delete(
        f"/api/v1/prompt-studio/qualification/{criterion_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    # Verify gone from list
    list_res = await async_client.get("/api/v1/prompt-studio/qualification", headers=headers)
    ids = [c["id"] for c in list_res.json()["data"]]
    assert criterion_id not in ids


@pytest.mark.asyncio
async def test_duplicate_code_rejected(async_client: AsyncClient, criteria_setup):
    setup = criteria_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Unique Test",
        "code": "unique_code",
        "criterion_type": "boolean",
    }, headers=headers)

    # Try to create with same code
    response = await async_client.post("/api/v1/prompt-studio/qualification", json={
        "label": "Another",
        "code": "unique_code",
        "criterion_type": "boolean",
    }, headers=headers)

    data = response.json()
    assert data["success"] is False
    assert "already exists" in data["error"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_access(async_client: AsyncClient):
    response = await async_client.get("/api/v1/prompt-studio/qualification")
    assert response.status_code in (401, 403)
