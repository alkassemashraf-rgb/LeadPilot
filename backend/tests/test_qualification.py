"""Tests for Qualification Config API — Mission 20."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str = "qual@test.com") -> dict:
    pwd = "password123"
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd, "full_name": "Qual Tester"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": pwd},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_res.json()["data"]["access_token"]
    ws_res = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


@pytest.mark.asyncio
async def test_get_qualification_config_lazy_creates(async_client: AsyncClient):
    """First GET creates a default config with standard questions and statuses."""
    headers = await get_auth_headers(async_client, "qual_lazy@test.com")

    res = await async_client.get("/api/v1/qualification-config", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True

    data = body["data"]
    assert data["version"] == 1

    # Check default questions
    questions = data["qualification_questions"]
    assert len(questions) >= 4  # At least 4 default questions
    labels = [q["label"] for q in questions]
    assert "Full Name" in labels
    assert "Company Email" in labels

    # Check default statuses
    statuses = data["qualification_statuses"]
    assert len(statuses) >= 3
    status_labels = [s["label"] for s in statuses]
    assert "Qualified" in status_labels
    assert "Unqualified" in status_labels


@pytest.mark.asyncio
async def test_update_qualification_config_increments_version(async_client: AsyncClient):
    """POST updates the config and increments the version number."""
    headers = await get_auth_headers(async_client, "qual_update@test.com")

    # First, trigger lazy creation
    await async_client.get("/api/v1/qualification-config", headers=headers)

    # Update with custom questions
    custom_questions = [
        {"label": "Company Size", "enabled": True, "order": 0},
        {"label": "Annual Revenue", "enabled": True, "order": 1},
    ]
    custom_statuses = [
        {"label": "Hot Lead", "color": "#ef4444", "enabled": True},
        {"label": "Cold Lead", "color": "#94a3b8", "enabled": True},
    ]

    res = await async_client.post(
        "/api/v1/qualification-config",
        json={
            "qualification_questions": custom_questions,
            "qualification_statuses": custom_statuses,
        },
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["version"] == 2

    # GET again to confirm persistence
    get_res = await async_client.get("/api/v1/qualification-config", headers=headers)
    data = get_res.json()["data"]
    assert data["version"] == 2
    assert len(data["qualification_questions"]) == 2
    assert data["qualification_questions"][0]["label"] == "Company Size"
    assert len(data["qualification_statuses"]) == 2


@pytest.mark.asyncio
async def test_qualification_idempotent_get(async_client: AsyncClient):
    """Multiple GETs return the same config without creating duplicates."""
    headers = await get_auth_headers(async_client, "qual_idempotent@test.com")

    res1 = await async_client.get("/api/v1/qualification-config", headers=headers)
    res2 = await async_client.get("/api/v1/qualification-config", headers=headers)

    assert res1.json()["data"]["version"] == res2.json()["data"]["version"]
    assert len(res1.json()["data"]["qualification_questions"]) == len(
        res2.json()["data"]["qualification_questions"]
    )
