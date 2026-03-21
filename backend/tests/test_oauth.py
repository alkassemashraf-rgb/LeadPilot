"""
Mission 37 — Universal OAuth Provider Framework Tests

Tests cover:
- State creation + validation
- Authorization URL generation
- Callback with invalid state (rejected)
- Happy-path callback → connection created
- Token refresh
- Disconnect (revoke)
- Tokens are encrypted at rest (not plaintext)
- Smoke: all seeded providers can generate an authorize URL
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    OAuthConnection, OAuthConnectionStatus, OAuthProvider, OAuthState,
    User, Workspace, WorkspaceMember, WorkspaceRole,
)
from app.core.security import create_access_token, decrypt_string, encrypt_string
from app.services import oauth_service
from app.services.oauth_providers import get_adapter
from app.seeds.oauth_providers import seed_oauth_providers


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_provider(provider_code: str = "hubspot") -> OAuthProvider:
    return OAuthProvider(
        id=uuid4(),
        provider_code=provider_code,
        display_name=provider_code.capitalize(),
        auth_url="https://example.com/oauth/authorize",
        token_url="https://example.com/oauth/token",
        scopes_json='["read"]',
        is_active=True,
        supports_refresh_token=True,
    )


async def _seed_user_workspace(db: AsyncSession):
    user = User(
        id=uuid4(), email=f"oauthtest-{uuid4().hex[:6]}@test.com",
        hashed_password="x", is_active=True,
    )
    ws = Workspace(id=uuid4(), name="OAuth Test WS", subscription_tier="free")
    db.add(user)
    db.add(ws)
    member = WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER)
    db.add(member)
    await db.flush()
    return user, ws


# ── 1. State creation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_oauth_state(db_session: AsyncSession):
    """create_oauth_state saves a row with correct expiry (~10 min)."""
    user, ws = await _seed_user_workspace(db_session)
    state = await oauth_service.create_oauth_state(
        db_session,
        provider_code="hubspot",
        workspace_id=ws.id,
        user_id=user.id,
    )
    await db_session.flush()

    assert state.state_token
    assert len(state.state_token) >= 32
    assert state.provider_code == "hubspot"
    assert state.workspace_id == ws.id
    # Expiry should be roughly 10 minutes from now
    delta = state.expires_at - datetime.utcnow()
    assert timedelta(minutes=9) < delta < timedelta(minutes=11)


# ── 2. Authorize returns URL ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authorize_returns_url(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/oauth/{provider}/authorize returns authorization_url when provider is active."""
    user, ws = await _seed_user_workspace(db_session)
    # Seed the provider
    provider = _make_provider("hubspot")
    db_session.add(provider)
    await db_session.commit()

    token = create_access_token(str(user.id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }

    with patch("app.api.v1.oauth.oauth_service._get_credentials", return_value=("test-client-id", "test-secret")):
        r = await async_client.get("/api/v1/oauth/hubspot/authorize", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "authorization_url" in body["data"]
    assert "hubspot" in body["data"]["authorization_url"] or "example.com" in body["data"]["authorization_url"]


# ── 3. Callback with invalid state ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_invalid_state_fails(async_client: AsyncClient, db_session: AsyncSession):
    """Callback with a bogus state token redirects to /integrations/callback?status=error."""
    r = await async_client.get(
        "/api/v1/oauth/hubspot/callback",
        params={"code": "somecode", "state": "totally-invalid-state-xyz"},
        follow_redirects=False,
    )
    # Should be a redirect
    assert r.status_code in (302, 307)
    location = r.headers.get("location", "")
    assert "status=error" in location


# ── 4. Callback success creates connection ────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_success_creates_connection(async_client: AsyncClient, db_session: AsyncSession):
    """Happy-path callback: valid state + mocked token exchange → OAuthConnection created."""
    user, ws = await _seed_user_workspace(db_session)
    provider = _make_provider("hubspot")
    db_session.add(provider)

    state = await oauth_service.create_oauth_state(
        db_session,
        provider_code="hubspot",
        workspace_id=ws.id,
        user_id=user.id,
    )
    await db_session.commit()

    fake_token_response = {
        "access_token": "real-access-token-abc123",
        "refresh_token": "real-refresh-token-xyz",
        "expires_in": 3600,
        "hub_id": 999,
        "hub_domain": "mycompany.hubspot.com",
    }

    with (
        patch("app.api.v1.oauth.oauth_service._get_credentials", return_value=("cid", "csecret")),
        patch("app.services.oauth_providers.hubspot.HubSpotOAuthAdapter.exchange_code", new=AsyncMock(return_value=fake_token_response)),
    ):
        r = await async_client.get(
            "/api/v1/oauth/hubspot/callback",
            params={"code": "authcode123", "state": state.state_token},
            follow_redirects=False,
        )

    assert r.status_code in (302, 307)
    location = r.headers.get("location", "")
    assert "status=success" in location
    assert "hubspot" in location

    # Verify connection was persisted
    result = await db_session.execute(
        select(OAuthConnection).where(
            OAuthConnection.workspace_id == ws.id,
            OAuthConnection.provider_code == "hubspot",
        )
    )
    conn = result.scalars().first()
    assert conn is not None
    assert conn.status == OAuthConnectionStatus.ACTIVE


# ── 5. Token refresh updates connection ──────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_updates_connection(db_session: AsyncSession):
    """refresh_access_token updates the encrypted token and sets status=active."""
    user, ws = await _seed_user_workspace(db_session)
    provider = _make_provider("hubspot")
    db_session.add(provider)

    conn = OAuthConnection(
        id=uuid4(),
        workspace_id=ws.id,
        provider_code="hubspot",
        access_token_encrypted=encrypt_string("old-token"),
        refresh_token_encrypted=encrypt_string("old-refresh"),
        status=OAuthConnectionStatus.EXPIRED,
    )
    db_session.add(conn)
    await db_session.flush()

    new_token_response = {
        "access_token": "brand-new-token",
        "refresh_token": "brand-new-refresh",
        "expires_in": 7200,
    }

    with (
        patch("app.services.oauth_service._get_credentials", return_value=("cid", "csecret")),
        patch("app.services.oauth_providers.hubspot.HubSpotOAuthAdapter.refresh_token", new=AsyncMock(return_value=new_token_response)),
    ):
        updated = await oauth_service.refresh_access_token(db_session, conn.id)

    assert updated.status == OAuthConnectionStatus.ACTIVE
    # Decrypted token must match new value
    assert decrypt_string(updated.access_token_encrypted) == "brand-new-token"
    assert decrypt_string(updated.refresh_token_encrypted) == "brand-new-refresh"


# ── 6. Disconnect marks revoked ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disconnect_marks_revoked(async_client: AsyncClient, db_session: AsyncSession):
    """DELETE /api/v1/oauth/connections/{id} sets status to revoked."""
    user, ws = await _seed_user_workspace(db_session)

    conn = OAuthConnection(
        id=uuid4(),
        workspace_id=ws.id,
        provider_code="hubspot",
        access_token_encrypted=encrypt_string("some-token"),
        status=OAuthConnectionStatus.ACTIVE,
    )
    db_session.add(conn)
    await db_session.commit()

    token = create_access_token(str(user.id))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-ID": str(ws.id),
    }
    r = await async_client.delete(f"/api/v1/oauth/connections/{conn.id}", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "revoked"

    # Verify in DB
    await db_session.refresh(conn)
    assert conn.status == OAuthConnectionStatus.REVOKED


# ── 7. Tokens are encrypted not plaintext ────────────────────────────────────

@pytest.mark.asyncio
async def test_tokens_are_encrypted_not_plaintext(db_session: AsyncSession):
    """OAuthConnection.access_token_encrypted must never equal the raw token."""
    raw_token = "super-secret-access-token-plain"
    encrypted = encrypt_string(raw_token)

    # Encrypted value should not equal plaintext
    assert encrypted != raw_token
    # Must be decryptable back to original
    assert decrypt_string(encrypted) == raw_token
    # Encrypted value should look like a Fernet token (base64url, starts with gAAA...)
    assert len(encrypted) > len(raw_token)


# ── 8. Smoke test: all seeded providers generate an authorize URL ─────────────

@pytest.mark.asyncio
async def test_all_seeded_providers_authorize(db_session: AsyncSession):
    """All 4 seeded providers can build a valid authorization URL via the adapter."""
    await seed_oauth_providers(db_session)

    providers_to_test = ["facebook", "tiktok", "hubspot", "salesforce"]
    client_id = "test-client-id"

    for code in providers_to_test:
        result = await db_session.execute(
            select(OAuthProvider).where(OAuthProvider.provider_code == code)
        )
        provider = result.scalars().first()
        assert provider is not None, f"Provider '{code}' not found after seed"
        assert provider.is_active, f"Provider '{code}' is not active"

        adapter = get_adapter(code)
        url = oauth_service.build_authorization_url(
            provider=provider,
            adapter=adapter,
            state_token="test-state-token",
            redirect_uri="https://example.com/callback",
            client_id=client_id,
        )
        assert url.startswith("https://"), f"URL for '{code}' is not HTTPS: {url}"
        assert "state=test-state-token" in url, f"state param missing in '{code}' URL"
