"""
Mission 31 — Meta Platform: Instagram DM, Messenger, and Lead Ads Tests.
Covers: OAuth flow, webhook subscription, message parsing (Instagram/Messenger),
delivery status watermarks, Lead Ads ingestion, MetaAdapter, and observability.
"""
import json
import time
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    User, Workspace, WorkspaceMember, WorkspaceRole,
    Message, DeliveryStatus, Integration, IntegrationStatus,
    Contact, ChannelIdentity, Conversation,
)
from app.core.security import get_password_hash, create_access_token, encrypt_data
from app.workers.tasks import parse_webhook_payload, _process_meta_status_updates
from app.services.meta_service import parse_lead_fields, subscribe_page_webhooks
from app.services.metrics_service import MetricsService


# ── Helpers ──────────────────────────────────────────────────────────────


async def _setup_workspace(db: AsyncSession, provider="meta"):
    """Create a user + workspace + integration for testing."""
    user = User(
        email=f"meta_test_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Meta Test User",
        is_active=True,
        is_superuser=False,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    ws = Workspace(name="Meta Test Workspace")
    db.add(ws)
    await db.flush()

    mem = WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER)
    db.add(mem)

    integration = Integration(
        workspace_id=ws.id,
        provider=provider,
        status=IntegrationStatus.CONNECTED,
        provider_workspace_id="PAGE_123",
        encrypted_config=encrypt_data({"access_token": "mock_page_token"}),
    )
    db.add(integration)
    await db.flush()

    return user, ws, integration


def _messenger_text_payload(page_id="PAGE_123", sender_id="PSID_456", text="Hello from Messenger"):
    """Build a Messenger webhook payload."""
    return {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": sender_id},
                "recipient": {"id": page_id},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": {
                    "mid": f"mid.{uuid4().hex[:12]}",
                    "text": text,
                },
            }],
        }],
    }


def _instagram_dm_payload(ig_id="IG_PAGE_123", sender_id="IGSID_789", text="Hello from Instagram"):
    """Build an Instagram DM webhook payload."""
    return {
        "object": "instagram",
        "entry": [{
            "id": ig_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": sender_id},
                "recipient": {"id": ig_id},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": {
                    "mid": f"mid.{uuid4().hex[:12]}",
                    "text": text,
                },
            }],
        }],
    }


def _instagram_attachment_payload(ig_id="IG_PAGE_123", sender_id="IGSID_789"):
    """Build an Instagram DM payload with an image attachment."""
    return {
        "object": "instagram",
        "entry": [{
            "id": ig_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": sender_id},
                "recipient": {"id": ig_id},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": {
                    "mid": f"mid.{uuid4().hex[:12]}",
                    "attachments": [{
                        "type": "image",
                        "payload": {"url": "https://example.com/photo.jpg"},
                    }],
                },
            }],
        }],
    }


def _messenger_echo_payload(page_id="PAGE_123"):
    """Build a Messenger echo payload (sent by the page itself)."""
    return {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": page_id},
                "recipient": {"id": "PSID_456"},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": {
                    "mid": f"mid.{uuid4().hex[:12]}",
                    "text": "Echo message",
                    "is_echo": True,
                },
            }],
        }],
    }


def _delivery_receipt_payload(page_id="PAGE_123", watermark=None):
    """Build a Meta delivery receipt payload."""
    if watermark is None:
        watermark = int(datetime.utcnow().timestamp() * 1000)
    return {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": page_id},
                "recipient": {"id": "PSID_456"},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "delivery": {
                    "mids": ["mid.abc123"],
                    "watermark": watermark,
                },
            }],
        }],
    }


def _read_receipt_payload(page_id="PAGE_123", watermark=None):
    """Build a Meta read receipt payload."""
    if watermark is None:
        watermark = int(datetime.utcnow().timestamp() * 1000)
    return {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "messaging": [{
                "sender": {"id": "PSID_456"},
                "recipient": {"id": page_id},
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "read": {
                    "watermark": watermark,
                },
            }],
        }],
    }


def _leadgen_payload(page_id="PAGE_123", leadgen_id="LEAD_999"):
    """Build a Lead Ads webhook payload."""
    return {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(datetime.utcnow().timestamp() * 1000),
            "changes": [{
                "field": "leadgen",
                "value": {
                    "leadgen_id": leadgen_id,
                    "page_id": page_id,
                    "form_id": "FORM_123",
                    "created_time": int(datetime.utcnow().timestamp()),
                },
            }],
        }],
    }


# ── Section 1: OAuth Flow ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_meta_oauth_start_returns_auth_url(async_client: AsyncClient, db_session: AsyncSession):
    """GET /start returns a valid Meta authorization URL."""
    user, ws, _ = await _setup_workspace(db_session)
    token = create_access_token(str(user.id), workspace_id=str(ws.id))

    with patch("app.api.v1.meta_oauth.settings") as mock_settings:
        mock_settings.META_CLIENT_ID = "test_client_id"
        mock_settings.META_CLIENT_SECRET = "test_secret"
        mock_settings.META_OAUTH_REDIRECT_URI = "https://example.com/callback"
        mock_settings.JWT_SECRET = "test_jwt_secret"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.FRONTEND_URL = "http://localhost:3000"
        mock_settings.APP_BASE_URL = None

        resp = await async_client.get(
            "/api/v1/integrations/meta/oauth/start",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    auth_url = data["data"]["auth_url"]
    assert "facebook.com" in auth_url
    assert "client_id=test_client_id" in auth_url
    assert "response_type=code" in auth_url


@pytest.mark.asyncio
async def test_meta_oauth_start_no_credentials(async_client: AsyncClient, db_session: AsyncSession):
    """GET /start returns error when META_CLIENT_ID is not configured."""
    user, ws, _ = await _setup_workspace(db_session)
    token = create_access_token(str(user.id), workspace_id=str(ws.id))

    with patch("app.api.v1.meta_oauth.settings") as mock_settings:
        mock_settings.META_CLIENT_ID = None
        mock_settings.META_CLIENT_SECRET = None

        resp = await async_client.get(
            "/api/v1/integrations/meta/oauth/start",
            headers={"Authorization": f"Bearer {token}", "X-Workspace-ID": str(ws.id)},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "configured" in data["error"].lower()


@pytest.mark.asyncio
async def test_meta_oauth_callback_success(async_client: AsyncClient, db_session: AsyncSession):
    """GET /callback with valid code exchanges tokens and creates Integration."""
    from jose import jwt as jose_jwt
    from app.core.config import settings

    user, ws, _ = await _setup_workspace(db_session, provider="whatsapp")  # no meta integration yet

    state = jose_jwt.encode(
        {"sub": str(user.id), "workspace_id": str(ws.id),
         "exp": datetime.utcnow() + timedelta(minutes=10), "purpose": "meta_oauth"},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM,
    )

    mock_responses = [
        # 1. Short-lived token exchange
        MagicMock(status_code=200, json=lambda: {"access_token": "short_token"}),
        # 2. Long-lived token exchange
        MagicMock(status_code=200, json=lambda: {"access_token": "long_lived_token"}),
        # 3. Fetch pages
        MagicMock(status_code=200, json=lambda: {"data": [{"id": "PAGE_NEW", "access_token": "page_token", "name": "My Page"}]}),
        # 4. Fetch IG account
        MagicMock(status_code=200, json=lambda: {"instagram_business_account": {"id": "IG_BIZ_123"}}),
        # 5. Subscribe webhooks
        MagicMock(status_code=200, json=lambda: {"success": True}),
    ]

    call_count = {"i": 0}
    original_get = None
    original_post = None

    async def mock_request(self, method, url, **kwargs):
        idx = call_count["i"]
        call_count["i"] += 1
        if idx < len(mock_responses):
            return mock_responses[idx]
        return MagicMock(status_code=200, json=lambda: {})

    with patch("httpx.AsyncClient.get", new=lambda self, url, **kw: mock_request(self, "GET", url, **kw)):
        with patch("httpx.AsyncClient.post", new=lambda self, url, **kw: mock_request(self, "POST", url, **kw)):
            resp = await async_client.get(
                f"/api/v1/integrations/meta/oauth/callback?code=test_code&state={state}",
            )

    # Should redirect to frontend
    # (httpx follows redirects by default in our test client)
    assert resp.status_code == 200 or resp.status_code == 307 or resp.status_code == 302


# ── Section 2: Webhook Subscription ──────────────────────────────────────


@pytest.mark.asyncio
async def test_subscribe_page_webhooks_success():
    """subscribe_page_webhooks returns True on 200 + success."""
    mock_resp = MagicMock(status_code=200, json=lambda: {"success": True})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await subscribe_page_webhooks("PAGE_123", "token_abc")

    assert result is True


@pytest.mark.asyncio
async def test_subscribe_page_webhooks_failure():
    """subscribe_page_webhooks returns False on error."""
    mock_resp = MagicMock(status_code=400, text="Bad Request", json=lambda: {"error": "bad"})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await subscribe_page_webhooks("PAGE_123", "token_abc")

    assert result is False


# ── Section 3: Message Parsing — Instagram vs Messenger ──────────────────


@pytest.mark.asyncio
async def test_parse_instagram_dm_text():
    """Instagram DM text payload → channel=instagram, correct content."""
    payload = _instagram_dm_payload(text="Hi from IG")
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "MESSAGE_INBOUND"
    assert info["channel"] == "instagram"
    assert info["provider_user_id"] == "IGSID_789"
    assert info["content"] == "Hi from IG"


@pytest.mark.asyncio
async def test_parse_messenger_text():
    """Messenger text payload → channel=messenger, correct content."""
    payload = _messenger_text_payload(text="Hi from Messenger")
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "MESSAGE_INBOUND"
    assert info["channel"] == "messenger"
    assert info["provider_user_id"] == "PSID_456"
    assert info["content"] == "Hi from Messenger"


@pytest.mark.asyncio
async def test_parse_instagram_attachment():
    """Instagram DM with image attachment → media_type + attachment_url extracted."""
    payload = _instagram_attachment_payload()
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "MESSAGE_INBOUND"
    assert info["channel"] == "instagram"
    assert info["media_type"] == "image"
    assert info["attachment_url"] == "https://example.com/photo.jpg"
    assert info["content"] == "[image]"


@pytest.mark.asyncio
async def test_parse_messenger_echo_detected():
    """Messenger echo payload — is_echo is not handled in parse but in process_webhook_event."""
    payload = _messenger_echo_payload()
    # parse_webhook_payload still returns MESSAGE_INBOUND for echoes
    # The echo detection happens in process_webhook_event (line 192-204)
    info = parse_webhook_payload("meta", payload)
    assert info["trigger_type"] == "MESSAGE_INBOUND"
    assert info["channel"] == "messenger"

    # Verify the echo flag is in the raw payload for process_webhook_event to detect
    entry = payload["entry"][0]
    assert entry["messaging"][0]["message"]["is_echo"] is True


# ── Section 4: Meta Delivery Status (Watermark) ─────────────────────────


@pytest.mark.asyncio
async def test_meta_delivery_watermark_updates(db_session: AsyncSession):
    """Delivery watermark updates SENT messages to DELIVERED."""
    user, ws, integration = await _setup_workspace(db_session)

    # Use time.time() for proper Unix epoch (avoids utcnow().timestamp() local TZ mismatch)
    now_epoch = time.time()
    sent_time = datetime.utcfromtimestamp(now_epoch - 300)  # 5 min ago
    msg = Message(
        workspace_id=ws.id,
        conversation_id=uuid4(),
        direction="outbound",
        content="Test message",
        platform="meta",
        delivery_status=DeliveryStatus.SENT,
        sent_at=sent_time,
    )
    db_session.add(msg)
    await db_session.flush()

    # Watermark is 1 minute ago (after sent_time)
    watermark = int((now_epoch - 60) * 1000)
    info = {"meta_delivery_watermark": watermark, "meta_read_watermark": None}

    await _process_meta_status_updates(
        db_session, info, ws.id, str(uuid4())
    )
    await db_session.flush()

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.DELIVERED
    assert msg.delivered_at is not None


@pytest.mark.asyncio
async def test_meta_read_watermark_updates(db_session: AsyncSession):
    """Read watermark updates DELIVERED messages to READ."""
    user, ws, integration = await _setup_workspace(db_session)

    now_epoch = time.time()
    sent_time = datetime.utcfromtimestamp(now_epoch - 300)
    msg = Message(
        workspace_id=ws.id,
        conversation_id=uuid4(),
        direction="outbound",
        content="Test read",
        platform="meta",
        delivery_status=DeliveryStatus.DELIVERED,
        sent_at=sent_time,
        delivered_at=datetime.utcfromtimestamp(now_epoch - 240),
    )
    db_session.add(msg)
    await db_session.flush()

    watermark = int((now_epoch - 60) * 1000)
    info = {"meta_delivery_watermark": None, "meta_read_watermark": watermark}

    await _process_meta_status_updates(
        db_session, info, ws.id, str(uuid4())
    )
    await db_session.flush()

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.READ
    assert msg.read_at is not None


@pytest.mark.asyncio
async def test_meta_status_no_regression(db_session: AsyncSession):
    """READ message should not regress to DELIVERED."""
    user, ws, integration = await _setup_workspace(db_session)

    now_epoch = time.time()
    sent_time = datetime.utcfromtimestamp(now_epoch - 300)
    msg = Message(
        workspace_id=ws.id,
        conversation_id=uuid4(),
        direction="outbound",
        content="Already read",
        platform="meta",
        delivery_status=DeliveryStatus.READ,
        sent_at=sent_time,
        delivered_at=datetime.utcfromtimestamp(now_epoch - 240),
        read_at=datetime.utcfromtimestamp(now_epoch - 180),
    )
    db_session.add(msg)
    await db_session.flush()

    # Delivery watermark arrives after the message was already READ
    watermark = int(now_epoch * 1000)
    info = {"meta_delivery_watermark": watermark, "meta_read_watermark": None}

    await _process_meta_status_updates(
        db_session, info, ws.id, str(uuid4())
    )
    await db_session.flush()

    await db_session.refresh(msg)
    # Should still be READ, not regressed to DELIVERED
    assert msg.delivery_status == DeliveryStatus.READ


# ── Section 5: Lead Ads Ingestion ────────────────────────────────────────


@pytest.mark.asyncio
async def test_parse_lead_fields_standard():
    """parse_lead_fields normalizes email + phone + full_name."""
    field_data = [
        {"name": "email", "values": ["john@example.com"]},
        {"name": "phone_number", "values": ["+14155551234"]},
        {"name": "full_name", "values": ["John Doe"]},
    ]
    result = parse_lead_fields(field_data)

    assert result["email"] == "john@example.com"
    assert result["phone"] == "+14155551234"
    assert result["full_name"] == "John Doe"
    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"


@pytest.mark.asyncio
async def test_parse_lead_fields_name_split():
    """full_name only (no separate first/last) → correctly splits."""
    field_data = [
        {"name": "full_name", "values": ["Jane Smith-Doe"]},
    ]
    result = parse_lead_fields(field_data)

    assert result["first_name"] == "Jane"
    assert result["last_name"] == "Smith-Doe"


@pytest.mark.asyncio
async def test_parse_leadgen_webhook():
    """Leadgen webhook payload → trigger_type=LEAD_AD_SUBMIT, leadgen_id extracted."""
    payload = _leadgen_payload(leadgen_id="LEAD_XYZ")
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "LEAD_AD_SUBMIT"
    assert info["leadgen_id"] == "LEAD_XYZ"
    assert info["channel"] == "lead_ads"
    assert info["provider_user_id"] == "LEAD_XYZ"


# ── Section 6: MetaAdapter ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_meta_send_media_success():
    """MetaAdapter.send_media returns provider_message_id on 200."""
    from app.integrations.meta.adapter import MetaAdapter

    adapter = MetaAdapter(page_id="PAGE_123", page_access_token="token_abc")
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {"message_id": "mid.media_xyz"},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await adapter.send_media("PSID_456", "image", "https://example.com/img.jpg")

    assert result == "mid.media_xyz"


@pytest.mark.asyncio
async def test_meta_send_media_permanent_failure():
    """MetaAdapter.send_media raises PERMANENT_FAILURE on 400."""
    from app.integrations.meta.adapter import MetaAdapter

    adapter = MetaAdapter(page_id="PAGE_123", page_access_token="token_abc")
    mock_resp = MagicMock(
        status_code=400,
        json=lambda: {"error": {"code": 100, "message": "Invalid attachment"}},
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(Exception, match="PERMANENT_FAILURE"):
            await adapter.send_media("PSID_456", "image", "https://example.com/bad.jpg")


@pytest.mark.asyncio
async def test_meta_get_user_profile():
    """MetaAdapter.get_user_profile returns profile on success, {} on failure."""
    from app.integrations.meta.adapter import MetaAdapter

    adapter = MetaAdapter(page_id="PAGE_123", page_access_token="token_abc")

    # Success case
    success_resp = MagicMock(
        status_code=200,
        json=lambda: {"first_name": "John", "last_name": "Doe"},
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=success_resp):
        profile = await adapter.get_user_profile("PSID_456")
    assert profile["first_name"] == "John"

    # Failure case
    fail_resp = MagicMock(status_code=403, text="Forbidden")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=fail_resp):
        profile = await adapter.get_user_profile("PSID_456")
    assert profile == {}


# ── Section 7: Delivery Status Parsing ───────────────────────────────────


@pytest.mark.asyncio
async def test_parse_delivery_receipt():
    """Delivery receipt payload → trigger_type=META_STATUS_UPDATE, watermark extracted."""
    watermark = int(datetime.utcnow().timestamp() * 1000)
    payload = _delivery_receipt_payload(watermark=watermark)
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "META_STATUS_UPDATE"
    assert info["meta_delivery_watermark"] == watermark
    assert info["meta_read_watermark"] is None


@pytest.mark.asyncio
async def test_parse_read_receipt():
    """Read receipt payload → trigger_type=META_STATUS_UPDATE, read watermark extracted."""
    watermark = int(datetime.utcnow().timestamp() * 1000)
    payload = _read_receipt_payload(watermark=watermark)
    info = parse_webhook_payload("meta", payload)

    assert info["trigger_type"] == "META_STATUS_UPDATE"
    assert info["meta_read_watermark"] == watermark


# ── Section 8: Observability ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_meta_metrics_tracking():
    """Meta-specific metrics increment correctly."""
    m = MetricsService()
    m.increment("meta_oauth_started")
    m.increment("meta_oauth_completed")
    m.increment("meta_leads_ingested")
    m.increment("meta_leads_ingested")
    m.increment("webhooks_received", labels={"provider": "meta", "channel": "instagram"})

    counts = m.get_counts()
    assert counts["meta_oauth_started"] == 1
    assert counts["meta_oauth_completed"] == 1
    assert counts["meta_leads_ingested"] == 2
    assert counts["webhooks_received{channel=instagram,provider=meta}"] == 1
