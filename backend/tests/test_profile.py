"""
Mission 21: Profile Update Tests
Tests PATCH /auth/me endpoint for user profile management.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ─────────────────────────────────────────────────────────


async def _signup_and_login(client: AsyncClient, email: str = "profile_user@example.com") -> str:
    """Create a user and return a JWT access token."""
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Original Name",
    })
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepassword123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    return login.json()["data"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_me_updates_full_name(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "profile_patch@example.com")

    response = await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Name"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_patch_me_strips_whitespace(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "profile_strip@example.com")

    response = await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "  Padded Name  "},
        headers=_auth(token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Padded Name"


@pytest.mark.asyncio
async def test_patch_me_empty_name_rejected(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "profile_empty@example.com")

    response = await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "   "},
        headers=_auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "empty" in data["error"].lower()


@pytest.mark.asyncio
async def test_patch_me_no_change_when_empty_body(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "profile_noop@example.com")

    response = await async_client.patch(
        "/api/v1/auth/me",
        json={},
        headers=_auth(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["full_name"] == "Original Name"


@pytest.mark.asyncio
async def test_get_me_reflects_patch(async_client: AsyncClient):
    token = await _signup_and_login(async_client, "profile_reflect@example.com")

    # Update
    await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Reflected Name"},
        headers=_auth(token),
    )

    # Read back
    response = await async_client.get("/api/v1/auth/me", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Reflected Name"


@pytest.mark.asyncio
async def test_patch_me_unauthenticated(async_client: AsyncClient):
    response = await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "No Auth"},
    )
    assert response.status_code in (401, 403)
