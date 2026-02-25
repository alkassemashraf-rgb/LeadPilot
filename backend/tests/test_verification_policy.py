"""
Mission 10.21 Tests — Verification Policy Alignment
Policy: Option A — 7-day grace window for integrations_connect
         Strict (no grace) for upgrade actions
"""
import asyncio
import secrets
import hashlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient


def _make_user(email, verified=False, grace_days_remaining=None):
    """Helper that returns kwargs for User creation."""
    from app.models.models import User
    from app.core.security import get_password_hash

    now = datetime.utcnow()
    kwargs = dict(
        email=email,
        hashed_password=get_password_hash("test_pass"),
        is_active=True,
    )
    if verified:
        kwargs["email_verified_at"] = now
    if grace_days_remaining is not None:
        kwargs["email_verification_expires_at"] = now + timedelta(days=grace_days_remaining)
    return kwargs


# ---------------------------------------------------------------------------
# require_email_state — unit tests (no HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_require_email_state_upgrade_blocks_unverified():
    """action='upgrade' must block an unverified user even within grace."""
    from app.api.deps import require_email_state
    from app.models.models import User
    from fastapi import HTTPException

    checker = require_email_state("upgrade")
    user = User(**_make_user("upgrade_test@example.com", verified=False, grace_days_remaining=5))

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_email_state_integrations_allows_within_grace():
    """action='integrations_connect' must allow unverified user within 7-day grace."""
    from app.api.deps import require_email_state
    from app.models.models import User

    checker = require_email_state("integrations_connect")
    user = User(**_make_user("grace_test@example.com", verified=False, grace_days_remaining=6))

    result = await checker(current_user=user)
    assert result.email == "grace_test@example.com"


@pytest.mark.asyncio
async def test_require_email_state_integrations_blocks_after_grace():
    """action='integrations_connect' must block if grace window expired."""
    from app.api.deps import require_email_state
    from app.models.models import User
    from fastapi import HTTPException

    checker = require_email_state("integrations_connect")
    # Grace expired yesterday
    user = User(**_make_user("expired_test@example.com", verified=False, grace_days_remaining=-1))

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)
    assert exc_info.value.status_code == 403
    assert "grace period" in exc_info.value.detail.lower() or "verification" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_require_email_state_verified_always_passes():
    """Verified user must pass all action checks."""
    from app.api.deps import require_email_state
    from app.models.models import User

    for action in ("upgrade", "integrations_connect", "verified"):
        checker = require_email_state(action)
        user = User(**_make_user(f"verified_{action}@example.com", verified=True))
        result = await checker(current_user=user)
        assert result is user


# ---------------------------------------------------------------------------
# /me endpoint — verify state fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_endpoint_returns_verification_fields(db_session: AsyncSession, async_client: AsyncClient):
    """GET /me must return email_verified_at, grace_remaining_days, requires_email_verification."""
    from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole
    from app.core.security import create_access_token

    now = datetime.utcnow()
    user = User(
        email="me_test@example.com",
        hashed_password="hashed",
        is_active=True,
        email_verification_expires_at=now + timedelta(days=5),
        email_verification_sent_at=now,
    )
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="ME Test WS")
    db_session.add(ws)
    await db_session.flush()

    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))
    await db_session.commit()

    user_id = user.id
    token = create_access_token(user_id, workspace_id=ws.id, expires_delta=timedelta(hours=1))

    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    payload = data["data"]
    assert payload["requires_email_verification"] is True
    assert payload["email_verified_at"] is None
    assert payload["verification_grace_remaining_days"] is not None
    assert payload["verification_grace_remaining_days"] >= 4  # Within 5 days grace


@pytest.mark.asyncio
async def test_me_endpoint_shows_verified_state(db_session: AsyncSession, async_client: AsyncClient):
    """GET /me shows requires_email_verification=False when user is verified."""
    from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole
    from app.core.security import create_access_token

    now = datetime.utcnow()
    user = User(
        email="me_verified@example.com",
        hashed_password="hashed",
        is_active=True,
        email_verified_at=now,
    )
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="ME Verified WS")
    db_session.add(ws)
    await db_session.flush()

    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))
    await db_session.commit()

    user_id = user.id
    token = create_access_token(user_id, workspace_id=ws.id, expires_delta=timedelta(hours=1))

    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["requires_email_verification"] is False
    assert payload["email_verified_at"] is not None
    assert payload["verification_grace_remaining_days"] is None


# ---------------------------------------------------------------------------
# Integration connect — within grace allowed, after grace blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_integrations_connect_allowed_within_grace():
    """
    OPTION A PROOF: require_email_state('integrations_connect') must pass
    for an unverified user who is within the 7-day grace window.
    This is the core guard unit-level proof for Policy Option A.
    """
    from app.api.deps import require_email_state
    from app.models.models import User

    checker = require_email_state("integrations_connect")
    now = datetime.utcnow()

    user = User(
        email="grace_http@example.com",
        hashed_password="hashed",
        is_active=True,
        email_verification_expires_at=now + timedelta(days=7),
        # email_verified_at = None — unverified but within grace
    )
    # Guard must return user without raising
    result = await checker(current_user=user)
    assert result.email == "grace_http@example.com", (
        "Grace-window: require_email_state should PASS for unverified user within 7-day window"
    )



@pytest.mark.asyncio
async def test_integrations_connect_blocked_after_grace(db_session: AsyncSession, async_client: AsyncClient):
    """Unverified user after grace expiry must be BLOCKED from connecting integration."""
    from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole
    from app.core.security import create_access_token

    now = datetime.utcnow()
    user = User(
        email="expired_connect@example.com",
        hashed_password="hashed",
        is_active=True,
        email_verification_expires_at=now - timedelta(days=1),  # Expired yesterday
        # email_verified_at = None
    )
    db_session.add(user)
    await db_session.flush()

    ws = Workspace(name="Expired WS")
    db_session.add(ws)
    await db_session.flush()

    db_session.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER))
    await db_session.commit()

    user_id, ws_id = user.id, ws.id
    token = create_access_token(user_id, workspace_id=ws_id, expires_delta=timedelta(hours=1))

    resp = await async_client.post(
        "/api/v1/integrations/zoho/connect",
        json={"config": {"access_token": "tok"}, "provider_workspace_id": "exp_org"},
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws_id)}
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["success"] is False
