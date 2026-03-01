"""
Mission 19: Catalog API Tests
Tests all 10 catalog endpoints return correct ResponseEnvelope structure.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Plan, PlanEntitlement, SystemModuleConfig,
    AutomationTemplate, AutomationTemplateVersion, TemplateUsageStat,
)
from datetime import datetime


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


# ── Public templates endpoint (Mission 33) ────────────────────────────


async def _seed_template(db: AsyncSession, slug: str = "test-tmpl", category: str = "lead_generation", is_featured: bool = False):
    """Create a minimal template + published version + usage stat for testing."""
    now = datetime.utcnow()
    tmpl = AutomationTemplate(
        slug=slug,
        name=f"Test Template {slug}",
        description=f"Description for {slug}",
        category=category,
        platforms=["whatsapp"],
        required_integrations=["whatsapp"],
        industry_tags=["test"],
        is_active=True,
        is_featured=is_featured,
        created_at=now,
        updated_at=now,
    )
    db.add(tmpl)
    await db.flush()

    ver = AutomationTemplateVersion(
        template_id=tmpl.id,
        version_number=1,
        builder_graph_json={"nodes": [], "edges": []},
        changelog="Seed",
        is_published=True,
        published_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(ver)

    stat = TemplateUsageStat(
        template_id=tmpl.id,
        clone_count=0,
        publish_count=0,
        active_flows_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(stat)
    await db.flush()
    return tmpl


@pytest.mark.asyncio
async def test_catalog_templates_returns_list(async_client: AsyncClient, db_session: AsyncSession):
    await _seed_template(db_session, slug="cat-tmpl-1")
    response = await async_client.get("/api/v1/catalog/templates")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    item = data["data"][0]
    assert "slug" in item
    assert "name" in item
    assert "category" in item
    assert "clone_count" in item
    assert "Cache-Control" in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_catalog_templates_category_filter(async_client: AsyncClient, db_session: AsyncSession):
    await _seed_template(db_session, slug="cat-lg-1", category="lead_generation")
    await _seed_template(db_session, slug="cat-sales-1", category="sales")
    response = await async_client.get("/api/v1/catalog/templates?category=lead_generation")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    for item in data["data"]:
        assert item["category"] == "lead_generation"


@pytest.mark.asyncio
async def test_catalog_templates_excludes_graph(async_client: AsyncClient, db_session: AsyncSession):
    await _seed_template(db_session, slug="cat-no-graph")
    response = await async_client.get("/api/v1/catalog/templates")
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert "builder_graph_json" not in item
        assert "variables" not in item
