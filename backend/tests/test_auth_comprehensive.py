"""
Comprehensive auth tests covering studio login, admin login, token validation,
role checks, and email verification edge cases.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole
from app.core.security import get_password_hash, create_access_token


# ── Helpers ──────────────────────────────────────────────────────────────


async def _create_user(
    db: AsyncSession,
    email: str,
    password: str = "testpass123",
    full_name: str = "Test User",
    is_superuser: bool = False,
    is_active: bool = True,
    verified: bool = True,
    with_workspace: bool = True,
) -> User:
    """Insert a user directly into DB. Returns the User object."""
    now = datetime.utcnow()
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_active=is_active,
        is_superuser=is_superuser,
        email_verified_at=now if verified else None,
        email_verification_expires_at=(
            now + timedelta(days=7) if not verified else None
        ),
    )
    db.add(user)
    await db.flush()

    if with_workspace:
        ws = Workspace(name=f"{email}'s Workspace")
        db.add(ws)
        await db.flush()
        mem = WorkspaceMember(
            user_id=user.id,
            workspace_id=ws.id,
            role=WorkspaceRole.OWNER,
        )
        db.add(mem)
        await db.flush()

    return user


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Studio Auth Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_studio_login_success(async_client: AsyncClient, db_session: AsyncSession):
    """Login with correct credentials returns access_token."""
    await _create_user(db_session, "studio_ok@test.com")
    r = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "studio_ok@test.com", "password": "testpass123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    assert "access_token" in d["data"]
    assert d["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_studio_login_wrong_password(async_client: AsyncClient, db_session: AsyncSession):
    """Login with wrong password returns error."""
    await _create_user(db_session, "studio_wrong@test.com")
    r = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "studio_wrong@test.com", "password": "wrongpassword"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    d = r.json()
    assert d["success"] is False


@pytest.mark.asyncio
async def test_studio_login_nonexistent(async_client: AsyncClient):
    """Login with non-existent user returns error."""
    r = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@test.com", "password": "anything"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    d = r.json()
    assert d["success"] is False


@pytest.mark.asyncio
async def test_studio_login_inactive_user(async_client: AsyncClient, db_session: AsyncSession):
    """Login with inactive user returns error."""
    await _create_user(db_session, "inactive@test.com", is_active=False)
    r = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@test.com", "password": "testpass123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    d = r.json()
    assert d["success"] is False
    assert "inactive" in d["error"].lower()


@pytest.mark.asyncio
async def test_get_me_valid_token(async_client: AsyncClient, db_session: AsyncSession):
    """GET /me with valid token returns user data."""
    user = await _create_user(db_session, "me_valid@test.com")
    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/auth/me", headers=_auth_header(token))
    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    assert d["data"]["email"] == "me_valid@test.com"


@pytest.mark.asyncio
async def test_get_me_no_token(async_client: AsyncClient):
    """GET /me with no auth header returns 401 or 403."""
    r = await async_client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_invalid_token(async_client: AsyncClient):
    """GET /me with garbage token returns 403."""
    r = await async_client.get(
        "/api/v1/auth/me",
        headers=_auth_header("not.a.real.jwt.token"),
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_expired_token(async_client: AsyncClient, db_session: AsyncSession):
    """GET /me with expired token returns 403."""
    user = await _create_user(db_session, "expired@test.com")
    token = create_access_token(user.id, expires_delta=timedelta(seconds=-1))
    r = await async_client.get("/api/v1/auth/me", headers=_auth_header(token))
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_duplicate_signup(async_client: AsyncClient, db_session: AsyncSession):
    """Signup with existing email returns error."""
    await _create_user(db_session, "dup@test.com")
    r = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": "dup@test.com", "password": "testpass123", "full_name": "Dup"},
    )
    d = r.json()
    assert d["success"] is False
    assert "already exists" in d["error"].lower()


# ── Admin Auth Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_login_success(async_client: AsyncClient, db_session: AsyncSession):
    """Admin login with superuser returns access_token."""
    await _create_user(db_session, "admin_ok@test.com", is_superuser=True)
    r = await async_client.post(
        "/api/v1/admin_auth/login",
        json={"email": "admin_ok@test.com", "password": "testpass123"},
    )
    d = r.json()
    assert d["success"] is True
    assert "access_token" in d["data"]


@pytest.mark.asyncio
async def test_admin_login_non_superuser(async_client: AsyncClient, db_session: AsyncSession):
    """Admin login with non-superuser is rejected."""
    await _create_user(db_session, "nonadmin@test.com", is_superuser=False)
    r = await async_client.post(
        "/api/v1/admin_auth/login",
        json={"email": "nonadmin@test.com", "password": "testpass123"},
    )
    d = r.json()
    assert d["success"] is False
    assert "admin" in d["error"].lower() or "privileges" in d["error"].lower()


@pytest.mark.asyncio
async def test_admin_login_wrong_password(async_client: AsyncClient, db_session: AsyncSession):
    """Admin login with wrong password returns error."""
    await _create_user(db_session, "admin_wrong@test.com", is_superuser=True)
    r = await async_client.post(
        "/api/v1/admin_auth/login",
        json={"email": "admin_wrong@test.com", "password": "wrongpass"},
    )
    d = r.json()
    assert d["success"] is False


@pytest.mark.asyncio
async def test_admin_login_inactive(async_client: AsyncClient, db_session: AsyncSession):
    """Admin login with inactive superuser returns error."""
    await _create_user(db_session, "admin_inactive@test.com", is_superuser=True, is_active=False)
    r = await async_client.post(
        "/api/v1/admin_auth/login",
        json={"email": "admin_inactive@test.com", "password": "testpass123"},
    )
    d = r.json()
    assert d["success"] is False
    assert "disabled" in d["error"].lower()


@pytest.mark.asyncio
async def test_admin_me_superuser(async_client: AsyncClient, db_session: AsyncSession):
    """Admin /me with superuser token returns admin data."""
    user = await _create_user(db_session, "admin_me@test.com", is_superuser=True)
    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/admin_auth/me", headers=_auth_header(token))
    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    assert d["data"]["is_superuser"] is True


@pytest.mark.asyncio
async def test_admin_me_non_superuser(async_client: AsyncClient, db_session: AsyncSession):
    """Admin /me with non-superuser token returns 403."""
    user = await _create_user(db_session, "admin_me_norole@test.com", is_superuser=False)
    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/admin_auth/me", headers=_auth_header(token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_me_no_token(async_client: AsyncClient):
    """Admin /me with no token returns 401 or 403."""
    r = await async_client.get("/api/v1/admin_auth/me")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_endpoint_non_superuser_blocked(async_client: AsyncClient, db_session: AsyncSession):
    """Non-superuser cannot access admin endpoints."""
    user = await _create_user(db_session, "admin_blocked@test.com", is_superuser=False)
    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/admin/modules", headers=_auth_header(token))
    assert r.status_code == 403


# ── Verification Grace Period Edge Cases ─────────────────────────────────


@pytest.mark.asyncio
async def test_unverified_within_grace_can_access(async_client: AsyncClient, db_session: AsyncSession):
    """Unverified user within grace period can access /me."""
    user = await _create_user(db_session, "grace_ok@test.com", verified=False)
    # Ensure grace period is in the future
    user.email_verification_expires_at = datetime.utcnow() + timedelta(days=7)
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/auth/me", headers=_auth_header(token))
    assert r.status_code == 200
    d = r.json()
    assert d["data"]["requires_email_verification"] is True


@pytest.mark.asyncio
async def test_unverified_past_grace_blocked(async_client: AsyncClient, db_session: AsyncSession):
    """Unverified user past grace period is blocked."""
    user = await _create_user(db_session, "grace_expired@test.com", verified=False)
    # Set grace period in the past
    user.email_verification_expires_at = datetime.utcnow() - timedelta(days=1)
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)
    r = await async_client.get("/api/v1/auth/me", headers=_auth_header(token))
    assert r.status_code == 403
    assert "grace period" in r.json().get("error", "").lower()
