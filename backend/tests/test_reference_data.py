"""
Mission 28: Reference Data Tests
Tests new catalog entries: template-categories, template-platforms,
and verifies automation-node-types includes required_module field.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_catalog_template_categories(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/template-categories")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 3

    keys = [item["key"] for item in data["data"]]
    assert "lead_generation" in keys
    assert "customer_support" in keys
    assert "sales" in keys

    for item in data["data"]:
        assert "key" in item
        assert "label" in item

    assert "Cache-Control" in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_catalog_template_platforms(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/template-platforms")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    keys = [item["key"] for item in data["data"]]
    assert "whatsapp" in keys
    assert "meta" in keys

    for item in data["data"]:
        assert "key" in item
        assert "label" in item


@pytest.mark.asyncio
async def test_node_types_include_required_module(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/automation-node-types")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Find the Zoho node — it should have required_module
    zoho_node = next(
        (n for n in data["data"] if n["key"] == "ZOHO_UPSERT_LEAD"), None
    )
    assert zoho_node is not None, "ZOHO_UPSERT_LEAD node type should exist"
    assert "required_module" in zoho_node
    assert zoho_node["required_module"] == "zoho_sync"

    # Other nodes should NOT have required_module set
    ai_node = next(
        (n for n in data["data"] if n["key"] == "AI_REPLY"), None
    )
    assert ai_node is not None
    assert ai_node.get("required_module") is None
