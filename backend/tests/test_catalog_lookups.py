"""
Mission 21: Catalog Lookup Tests
Tests all 8 new static catalog endpoints added for data-driven dropdowns.
"""
import pytest
from httpx import AsyncClient


# All new Mission 21 catalog endpoints with a sample of expected keys
NEW_LOOKUP_ENDPOINTS = [
    ("timezones", ["UTC", "US/Eastern", "Asia/Dubai"]),
    ("languages", ["en", "ar", "es"]),
    ("ai-models", ["gemini-1.5-pro", "gemini-2.0-flash"]),
    ("dedupe-strategies", ["EMAIL", "PHONE", "EMAIL_OR_PHONE"]),
    ("event-sources", ["webhook", "runtime", "dispatch", "inbox"]),
    ("event-outcomes", ["success", "failure", "skipped"]),
    ("audit-actions", ["user_login", "update_profile", "automation_create"]),
    ("contact-fields", ["first_name", "email", "phone"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,expected_keys", NEW_LOOKUP_ENDPOINTS)
async def test_lookup_endpoint_returns_data(
    async_client: AsyncClient, endpoint: str, expected_keys: list
):
    response = await async_client.get(f"/api/v1/catalog/{endpoint}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    items = data["data"]
    assert isinstance(items, list)
    assert len(items) >= 1

    # Every item must have key + label
    for item in items:
        assert "key" in item, f"Item missing 'key' in {endpoint}"
        assert "label" in item, f"Item missing 'label' in {endpoint}"

    # Spot-check expected keys are present
    actual_keys = [item["key"] for item in items]
    for key in expected_keys:
        assert key in actual_keys, f"Expected key '{key}' in /catalog/{endpoint}"


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,expected_keys", NEW_LOOKUP_ENDPOINTS)
async def test_lookup_endpoint_cache_header(
    async_client: AsyncClient, endpoint: str, expected_keys: list
):
    response = await async_client.get(f"/api/v1/catalog/{endpoint}")
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_contact_fields_have_required_flag(async_client: AsyncClient):
    response = await async_client.get("/api/v1/catalog/contact-fields")
    data = response.json()
    for item in data["data"]:
        assert "required" in item, f"Contact field '{item['key']}' missing 'required' flag"
        assert isinstance(item["required"], bool)

    # first_name should be required, phone should not
    fields_map = {f["key"]: f for f in data["data"]}
    assert fields_map["first_name"]["required"] is True
    assert fields_map["phone"]["required"] is False
