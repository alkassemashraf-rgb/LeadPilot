"""
Mission 19: Catalog API Tests
Tests all 10 catalog endpoints return correct ResponseEnvelope structure.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Plan, PlanEntitlement, SystemModuleConfig


# ── Seed helpers ─────────────────────────────────────────────────────


async def _seed_plan(db: AsyncSession):
    plan = Plan(
        name="test_catalog_plan",
        display_name="Test Catalog Plan",
        sort_order=0,
        is_active=True,
        description="A plan for catalog tests",
    )
    db.add(plan)
    await db.flush()
    ent = PlanEntitlement(plan_id=plan.id, module_key="analytics", hard_limit=100)
    db.add(ent)
    await db.flush()
    return plan


async def _seed_module(db: AsyncSession):
    mod = SystemModuleConfig(
        module_name="test_catalog_module",
        is_enabled=True,
    )
    db.add(mod)
    await db.flush()
    return mod


# ── DB-backed endpoints ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_catalog_plans(async_client: AsyncClient, db_session: AsyncSession):
    await _seed_plan(db_session)
    response = await async_client.get("/api/v1/catalog/plans")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    plan = data["data"][0]
    assert "name" in plan
    assert "display_name" in plan
    assert "entitlements" in plan
    assert "Cache-Control" in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_catalog_tiers_is_plans_alias(
    async_client: AsyncClient, db_session: AsyncSession
):
    await _seed_plan(db_session)
    response = await async_client.get("/api/v1/catalog/tiers")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_catalog_modules(async_client: AsyncClient, db_session: AsyncSession):
    await _seed_module(db_session)
    response = await async_client.get("/api/v1/catalog/modules")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert any(m["key"] == "test_catalog_module" for m in data["data"])
    for m in data["data"]:
        assert "key" in m
        assert "label" in m
        assert "is_enabled" in m
    assert "Cache-Control" in response.headers


# ── Static (registry-backed) endpoints ───────────────────────────────


STATIC_ENDPOINTS = [
    ("workspace-roles", ["owner", "member", "viewer"]),
    ("admin-roles", ["agency_owner", "agency_admin", "agency_operator", "agency_viewer"]),
    ("integration-providers", ["zoho", "whatsapp", "meta"]),
    (
        "automation-node-types",
        ["AI_REPLY", "SEND_MESSAGE", "HUMAN_HANDOVER", "TAG_CONTACT"],
    ),
    ("automation-trigger-types", ["MESSAGE_INBOUND", "LEAD_AD_SUBMIT"]),
    ("conversation-statuses", ["bot_active", "human_takeover", "closed"]),
    ("message-delivery-statuses", ["pending", "sending", "sent", "delivered", "read", "failed", "dead_letter"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,expected_keys", STATIC_ENDPOINTS)
async def test_catalog_static_endpoints(
    async_client: AsyncClient, endpoint: str, expected_keys: list
):
    response = await async_client.get(f"/api/v1/catalog/{endpoint}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    actual_keys = [item["key"] for item in data["data"]]
    for key in expected_keys:
        assert key in actual_keys, f"Expected key '{key}' in {endpoint} catalog"
    # Every item must have key + label
    for item in data["data"]:
        assert "key" in item
        assert "label" in item
    # Cache header
    assert "Cache-Control" in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_catalog_unknown_endpoint_404(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/nonexistent")
    assert response.status_code in (404, 405)


@pytest.mark.asyncio
async def test_catalog_integration_providers_have_fields(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/integration-providers")
    data = response.json()
    for provider in data["data"]:
        assert "fields" in provider
        assert isinstance(provider["fields"], list)
        for field in provider["fields"]:
            assert "name" in field
            assert "label" in field
            assert "type" in field
