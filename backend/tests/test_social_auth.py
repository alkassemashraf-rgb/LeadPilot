"""
Mission 38 — Social Login (Facebook + TikTok) Tests

Tests cover:
1. test_facebook_oauth_start_returns_url
2. test_tiktok_oauth_start_returns_url
3. test_oauth_callback_existing_identity_logs_in
4. test_oauth_callback_existing_email_links_identity
5. test_oauth_callback_new_user_creates_user_and_workspace
6. test_oauth_callback_missing_email_uses_placeholder
7. test_invalid_state_rejected
8. test_duplicate_identity_not_created
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    OAuthProvider,
    OAuthState,
    User,
    UserIdentity,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.services import oauth_service


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_provider(provider_code: str, auth_url: str, token_url: str) -> OAuthProvider:
    return OAuthProvider(
        id=uuid4(),
        provider_code=provider_code,
        display_name=provider_code.capitalize(),
        auth_url=auth_url,
        token_url=token_url,
        scopes_json='["public_profile","email"]',
        is_active=True,
        supports_refresh_token=False,
    )


async def _seed_facebook_provider(db: AsyncSession) -> OAuthProvider:
    p = _make_provider("facebook", "https://www.facebook.com/v18.0/dialog/oauth",
                       "https://graph.facebook.com/v18.0/oauth/access_token")
    db.add(p)
    await db.flush()
    return p


async def _seed_tiktok_provider(db: AsyncSession) -> OAuthProvider:
    p = _make_provider("tiktok", "https://www.tiktok.com/v2/auth/authorize/",
                       "https://open.tiktokapis.com/v2/oauth/token/")
    db.add(p)
    await db.flush()
    return p


async def _create_social_state(db: AsyncSession, provider_code: str) -> OAuthState:
    state = await oauth_service.create_oauth_state(
        db,
        provider_code=provider_code,
        workspace_id=None,
        user_id=None,
        purpose="social_auth",
    )
    await db.flush()
    return state


_FACEBOOK_PROFILE = {
    "provider_user_id": "fb_user_123",
    "email": "fb@example.com",
    "full_name": "Facebook User",
    "avatar_url": "https://example.com/pic.jpg",
}

_TIKTOK_PROFILE_NO_EMAIL = {
    "provider_user_id": "tt_open_456",
    "email": None,
    "full_name": "TikTok User",
    "avatar_url": "https://example.com/tt.jpg",
}

_FAKE_TOKEN = {"access_token": "fake-access-token-xyz", "token_type": "bearer"}


# ── 1. Facebook start returns URL ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_facebook_oauth_start_returns_url(async_client: AsyncClient, db_session: AsyncSession):
    """GET /auth/oauth/facebook/start returns authorization_url pointing to Facebook."""
    await _seed_facebook_provider(db_session)
    await db_session.commit()

    with patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("fb-client-id", "fb-secret")):
        r = await async_client.get("/api/v1/auth/oauth/facebook/start")

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    url = body["data"]["authorization_url"]
    assert "facebook.com" in url
    assert "fb-client-id" in url


# ── 2. TikTok start returns URL ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tiktok_oauth_start_returns_url(async_client: AsyncClient, db_session: AsyncSession):
    """GET /auth/oauth/tiktok/start returns authorization_url pointing to TikTok."""
    await _seed_tiktok_provider(db_session)
    await db_session.commit()

    with patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("tt-client-key", "tt-secret")):
        r = await async_client.get("/api/v1/auth/oauth/tiktok/start")

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    url = body["data"]["authorization_url"]
    assert "tiktok.com" in url


# ── 3. Callback with existing identity logs user in ───────────────────────────

@pytest.mark.asyncio
async def test_oauth_callback_existing_identity_logs_in(async_client: AsyncClient, db_session: AsyncSession):
    """Callback for a known (provider_code, provider_user_id) issues JWT without creating new user."""
    await _seed_facebook_provider(db_session)

    # Create existing user + identity
    user = User(id=uuid4(), email="existing@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(id=uuid4(), name="Existing WS")
    db_session.add(ws)
    await db_session.flush()
    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    identity = UserIdentity(
        user_id=user.id,
        provider_code="facebook",
        provider_user_id="fb_user_123",
        provider_email="existing@example.com",
    )
    db_session.add(identity)

    state = await _create_social_state(db_session, "facebook")
    await db_session.commit()

    with (
        patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("cid", "csec")),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.exchange_code",
              new=AsyncMock(return_value=_FAKE_TOKEN)),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.fetch_user_profile",
              new=AsyncMock(return_value=_FACEBOOK_PROFILE)),
    ):
        r = await async_client.get(
            "/api/v1/auth/oauth/facebook/callback",
            params={"code": "authcode", "state": state.state_token},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["new_user"] is False

    # No duplicate identity created
    result = await db_session.execute(
        select(UserIdentity).where(UserIdentity.provider_user_id == "fb_user_123")
    )
    identities = result.scalars().all()
    assert len(identities) == 1


# ── 4. Callback with email match links identity ───────────────────────────────

@pytest.mark.asyncio
async def test_oauth_callback_existing_email_links_identity(async_client: AsyncClient, db_session: AsyncSession):
    """Callback where provider email matches existing User links a new UserIdentity."""
    await _seed_facebook_provider(db_session)

    user = User(id=uuid4(), email="fb@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(id=uuid4(), name="Email Match WS")
    db_session.add(ws)
    await db_session.flush()
    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    state = await _create_social_state(db_session, "facebook")
    await db_session.commit()

    with (
        patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("cid", "csec")),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.exchange_code",
              new=AsyncMock(return_value=_FAKE_TOKEN)),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.fetch_user_profile",
              new=AsyncMock(return_value=_FACEBOOK_PROFILE)),
    ):
        r = await async_client.get(
            "/api/v1/auth/oauth/facebook/callback",
            params={"code": "authcode", "state": state.state_token},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["new_user"] is False

    # Identity was linked to the pre-existing user
    result = await db_session.execute(
        select(UserIdentity).where(
            UserIdentity.provider_code == "facebook",
            UserIdentity.provider_user_id == "fb_user_123",
        )
    )
    identity = result.scalars().first()
    assert identity is not None
    assert identity.user_id == user.id

    # No duplicate user created
    users_result = await db_session.execute(select(User).where(User.email == "fb@example.com"))
    assert len(users_result.scalars().all()) == 1


# ── 5. Callback creates new user and workspace ────────────────────────────────

@pytest.mark.asyncio
async def test_oauth_callback_new_user_creates_user_and_workspace(async_client: AsyncClient, db_session: AsyncSession):
    """Callback for brand-new user creates User + Workspace + UserIdentity."""
    await _seed_facebook_provider(db_session)
    state = await _create_social_state(db_session, "facebook")
    await db_session.commit()

    profile = {**_FACEBOOK_PROFILE, "provider_user_id": "fb_new_999", "email": "newuser@example.com"}

    with (
        patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("cid", "csec")),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.exchange_code",
              new=AsyncMock(return_value=_FAKE_TOKEN)),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.fetch_user_profile",
              new=AsyncMock(return_value=profile)),
    ):
        r = await async_client.get(
            "/api/v1/auth/oauth/facebook/callback",
            params={"code": "authcode", "state": state.state_token},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["new_user"] is True

    # User exists
    user_result = await db_session.execute(select(User).where(User.email == "newuser@example.com"))
    user = user_result.scalars().first()
    assert user is not None

    # Workspace created
    ws_result = await db_session.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
    )
    assert ws_result.scalars().first() is not None

    # UserIdentity created
    id_result = await db_session.execute(
        select(UserIdentity).where(UserIdentity.provider_user_id == "fb_new_999")
    )
    assert id_result.scalars().first() is not None


# ── 6. Missing email uses placeholder ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_oauth_callback_missing_email_uses_placeholder(async_client: AsyncClient, db_session: AsyncSession):
    """TikTok (no email) creates user with placeholder email and flags social_email_missing."""
    await _seed_tiktok_provider(db_session)
    state = await _create_social_state(db_session, "tiktok")
    await db_session.commit()

    with (
        patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("ttkey", "ttsec")),
        patch("app.services.oauth_providers.tiktok.TikTokOAuthAdapter.exchange_code",
              new=AsyncMock(return_value=_FAKE_TOKEN)),
        patch("app.services.oauth_providers.tiktok.TikTokOAuthAdapter.fetch_user_profile",
              new=AsyncMock(return_value=_TIKTOK_PROFILE_NO_EMAIL)),
    ):
        r = await async_client.get(
            "/api/v1/auth/oauth/tiktok/callback",
            params={"code": "authcode", "state": state.state_token},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["new_user"] is True

    # Placeholder email used
    user_result = await db_session.execute(
        select(User).where(User.email == "tiktok_tt_open_456@placeholder.local")
    )
    user = user_result.scalars().first()
    assert user is not None

    # Identity has metadata_json flagging missing email
    import json
    id_result = await db_session.execute(
        select(UserIdentity).where(UserIdentity.provider_user_id == "tt_open_456")
    )
    identity = id_result.scalars().first()
    assert identity is not None
    assert identity.metadata_json is not None
    meta = json.loads(identity.metadata_json)
    assert meta.get("social_email_missing") is True


# ── 7. Invalid state is rejected ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_state_rejected(async_client: AsyncClient, db_session: AsyncSession):
    """Callback with a bogus state token returns error (not 500, not success)."""
    await _seed_facebook_provider(db_session)
    await db_session.commit()

    r = await async_client.get(
        "/api/v1/auth/oauth/facebook/callback",
        params={"code": "anycode", "state": "totally-invalid-state-xyz-abc"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"] is not None


# ── 8. Duplicate identity not created ────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_identity_not_created(async_client: AsyncClient, db_session: AsyncSession):
    """Second login with same provider identity reuses existing UserIdentity — no duplicate."""
    await _seed_facebook_provider(db_session)

    user = User(id=uuid4(), email="repeat@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(id=uuid4(), name="Repeat WS")
    db_session.add(ws)
    await db_session.flush()
    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))

    # Identity already exists
    identity = UserIdentity(
        user_id=user.id,
        provider_code="facebook",
        provider_user_id="fb_repeat_777",
        provider_email="repeat@example.com",
    )
    db_session.add(identity)

    state = await _create_social_state(db_session, "facebook")
    await db_session.commit()

    profile = {**_FACEBOOK_PROFILE, "provider_user_id": "fb_repeat_777", "email": "repeat@example.com"}

    with (
        patch("app.api.v1.social_auth.oauth_service._get_credentials", return_value=("cid", "csec")),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.exchange_code",
              new=AsyncMock(return_value=_FAKE_TOKEN)),
        patch("app.services.oauth_providers.facebook.FacebookOAuthAdapter.fetch_user_profile",
              new=AsyncMock(return_value=profile)),
    ):
        r = await async_client.get(
            "/api/v1/auth/oauth/facebook/callback",
            params={"code": "authcode", "state": state.state_token},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["new_user"] is False

    # Still only one identity
    result = await db_session.execute(
        select(UserIdentity).where(UserIdentity.provider_user_id == "fb_repeat_777")
    )
    identities = result.scalars().all()
    assert len(identities) == 1

    # Still only one user
    user_result = await db_session.execute(select(User).where(User.email == "repeat@example.com"))
    assert len(user_result.scalars().all()) == 1
