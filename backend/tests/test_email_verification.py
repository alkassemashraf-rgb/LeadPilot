"""
Tests for Email Verification Flow (Mission 10.20)
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_creates_verification_outbox(db_session: AsyncSession, async_client: AsyncClient):
    """Signup must create an EmailOutbox entry for verify_email type."""
    from app.models.models import EmailOutbox, EmailOutboxStatus

    with patch("app.workers.email_tasks.send_email_task_v2") as mock_task:
        mock_task.delay = AsyncMock()
        
        response = await async_client.post("/api/v1/auth/signup", json={
            "email": "verify_test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    from sqlmodel import select
    result = await db_session.execute(
        select(EmailOutbox).where(EmailOutbox.email_type == "verify_email")
    )
    outboxes = result.scalars().all()
    assert len(outboxes) >= 1, "Signup should create a verify_email EmailOutbox entry"


@pytest.mark.asyncio
async def test_verify_email_sets_verified_at(db_session: AsyncSession, async_client: AsyncClient):
    """GET /verify-email?token=... must set email_verified_at on user."""
    import secrets
    import hashlib
    from app.models.models import User, EmailVerificationToken
    
    # Create user directly  
    now = datetime.utcnow()
    user = User(
        email="to_verify@example.com",
        hashed_password="hashed",
        is_active=True,
        email_verification_expires_at=now + timedelta(days=7),
        email_verification_sent_at=now,
    )
    db_session.add(user)
    await db_session.flush()
    
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    db_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=7),
    )
    db_session.add(db_token)
    await db_session.commit()
    
    user_id = user.id
    
    response = await async_client.get(f"/api/v1/auth/verify-email?token={token}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    refreshed = await db_session.get(User, user_id)
    assert refreshed.email_verified_at is not None


@pytest.mark.asyncio
async def test_resend_verification_rate_limit(async_client: AsyncClient):
    """Resend verification should respect rate limiting (mocked)."""
    # Mock Redis to return count > 5 on the 6th call
    from unittest.mock import AsyncMock, MagicMock
    
    call_count = [0]
    
    async def mock_incr(key):
        call_count[0] += 1
        return call_count[0]

    mock_redis = AsyncMock()
    mock_redis.incr = mock_incr
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()
    
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        # First 5 should pass
        for _ in range(5):
            resp = await async_client.post("/api/v1/auth/resend-verification", json={
                "email": "rate_limit_test@example.com"
            })
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        # 6th request: mock returns 6, should be blocked
        resp = await async_client.post("/api/v1/auth/resend-verification", json={
            "email": "rate_limit_test@example.com"
        })
        assert resp.status_code == 200  # HTTP still 200 
        data = resp.json()
        assert data["success"] is False
        assert "Too many" in (data.get("error") or "")


@pytest.mark.asyncio
async def test_integrations_connect_blocked_if_unverified(db_session: AsyncSession, async_client: AsyncClient):
    """Integration connect should return 403 if user email is not verified."""
    from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole
    from app.core import security
    
    user = User(
        email="unverified_integ@example.com",
        hashed_password=security.get_password_hash("password"),
        is_active=True,
        # email_verified_at = None (not verified)
    )
    db_session.add(user)
    await db_session.flush()
    
    ws = Workspace(name="Test WS Integ")
    db_session.add(ws)
    await db_session.flush()
    
    member = WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER)
    db_session.add(member)
    await db_session.commit()
    
    user_id = user.id
    ws_id = ws.id
    
    from datetime import timedelta
    from app.core.security import create_access_token
    token = create_access_token(user_id, workspace_id=ws_id, expires_delta=timedelta(hours=1))
    
    response = await async_client.post(
        "/api/v1/integrations/zoho/connect",
        json={"config": {"access_token": "test"}, "provider_workspace_id": "test_org"},
        headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws_id)}
    )
    
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
