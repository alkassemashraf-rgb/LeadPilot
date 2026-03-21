"""
Mission 30 — WhatsApp Cloud Production Hardening Tests.
Covers: signature verification, payload parsing, status webhooks,
phone normalization, dead-letter queue, and payload size limit.
"""
import hmac
import hashlib
import json
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    User, Workspace, WorkspaceMember, WorkspaceRole,
    Message, DeliveryStatus, Integration, IntegrationStatus,
    Contact, ChannelIdentity, Conversation,
)
from app.core.security import get_password_hash, create_access_token, encrypt_data
from app.workers.tasks import parse_webhook_payload
from app.domain.contacts import normalize_phone


# ── Helpers ──────────────────────────────────────────────────────────────


async def _setup_workspace(db: AsyncSession):
    """Create a user + workspace + integration for testing."""
    user = User(
        email=f"wa_test_{uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="WA Test User",
        is_active=True,
        is_superuser=False,
        email_verified_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()

    ws = Workspace(name="WA Test Workspace")
    db.add(ws)
    await db.flush()

    mem = WorkspaceMember(user_id=user.id, workspace_id=ws.id, role=WorkspaceRole.OWNER)
    db.add(mem)

    integration = Integration(
        workspace_id=ws.id,
        provider="whatsapp",
        status=IntegrationStatus.CONNECTED,
        provider_workspace_id="123456789",
        encrypted_config=encrypt_data({"access_token": "mock_token"}),
    )
    db.add(integration)
    await db.flush()

    return user, ws, integration


def _whatsapp_text_payload(phone_number_id="123456789", sender="14155551234", text="Hello"):
    """Build a realistic WhatsApp Cloud API webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "BIZ_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": phone_number_id},
                    "contacts": [{"profile": {"name": "Test Contact"}, "wa_id": sender}],
                    "messages": [{
                        "from": sender,
                        "id": f"wamid.{uuid4().hex}",
                        "timestamp": str(int(datetime.utcnow().timestamp())),
                        "text": {"body": text},
                        "type": "text",
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def _whatsapp_image_payload(phone_number_id="123456789", sender="14155551234"):
    """Build a WhatsApp image message payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "BIZ_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": phone_number_id},
                    "contacts": [{"profile": {"name": "Test Contact"}, "wa_id": sender}],
                    "messages": [{
                        "from": sender,
                        "id": f"wamid.{uuid4().hex}",
                        "timestamp": str(int(datetime.utcnow().timestamp())),
                        "type": "image",
                        "image": {
                            "id": "media_id_123",
                            "mime_type": "image/jpeg",
                            "sha256": "abc123",
                            "caption": "Check this out",
                        },
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def _whatsapp_status_payload(provider_message_id, status, phone_number_id="123456789"):
    """Build a WhatsApp delivery status webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "BIZ_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": phone_number_id},
                    "statuses": [{
                        "id": provider_message_id,
                        "status": status,
                        "timestamp": str(int(datetime.utcnow().timestamp())),
                        "recipient_id": "14155551234",
                    }],
                },
                "field": "messages",
            }],
        }],
    }


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Generate a valid X-Hub-Signature-256 header value."""
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ── Test 1: Signature Verification ───────────────────────────────────────


@pytest.mark.asyncio
async def test_whatsapp_webhook_valid_signature(async_client: AsyncClient, db_session: AsyncSession):
    """Valid HMAC signature → 200."""
    await _setup_workspace(db_session)
    payload = _whatsapp_text_payload()
    payload_bytes = json.dumps(payload).encode()
    secret = "test_secret_123"

    with (
        patch("app.api.v1.webhooks.settings") as mock_settings,
        patch("app.api.v1.webhooks.process_webhook_event") as mock_task,
    ):
        mock_settings.META_APP_SECRET = secret
        mock_settings.WEBHOOK_MAX_PAYLOAD_BYTES = 1_048_576
        mock_settings.WHATSAPP_VERIFY_TOKEN = "test"
        mock_task.delay = lambda *a, **kw: None
        signature = _sign_payload(payload_bytes, secret)
        r = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_signature(async_client: AsyncClient, db_session: AsyncSession):
    """Wrong HMAC + META_APP_SECRET configured → 403."""
    await _setup_workspace(db_session)
    payload = _whatsapp_text_payload()
    payload_bytes = json.dumps(payload).encode()

    with patch("app.api.v1.webhooks.settings") as mock_settings:
        mock_settings.META_APP_SECRET = "real_secret"
        mock_settings.WEBHOOK_MAX_PAYLOAD_BYTES = 1_048_576
        mock_settings.WHATSAPP_VERIFY_TOKEN = "test"
        r = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid_signature",
            },
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_no_secret_configured(async_client: AsyncClient, db_session: AsyncSession):
    """No META_APP_SECRET → still accepts (MVP fallback)."""
    await _setup_workspace(db_session)
    payload = _whatsapp_text_payload()
    payload_bytes = json.dumps(payload).encode()

    with (
        patch("app.api.v1.webhooks.settings") as mock_settings,
        patch("app.api.v1.webhooks.process_webhook_event") as mock_task,
    ):
        mock_settings.META_APP_SECRET = None
        mock_settings.WEBHOOK_MAX_PAYLOAD_BYTES = 1_048_576
        mock_settings.WHATSAPP_VERIFY_TOKEN = "test"
        mock_task.delay = lambda *a, **kw: None
        r = await async_client.post(
            "/api/v1/webhooks/whatsapp",
            content=payload_bytes,
            headers={"Content-Type": "application/json"},
        )
    assert r.status_code == 200


# ── Test 2: Payload Parsing ──────────────────────────────────────────────


def test_parse_text_message():
    """Standard WhatsApp text payload → correct normalized fields."""
    payload = _whatsapp_text_payload(sender="14155551234", text="Hi there")
    result = parse_webhook_payload("whatsapp", payload)

    assert result["trigger_type"] == "MESSAGE_INBOUND"
    assert result["provider_user_id"] == "14155551234"
    assert result["content"] == "Hi there"
    assert result["first_name"] == "Test Contact"
    assert result["media_id"] is None


def test_parse_media_message():
    """Image payload → media_id, media_type extracted."""
    payload = _whatsapp_image_payload()
    result = parse_webhook_payload("whatsapp", payload)

    assert result["trigger_type"] == "MESSAGE_INBOUND"
    assert result["media_id"] == "media_id_123"
    assert result["media_type"] == "image"
    assert result["mime_type"] == "image/jpeg"
    assert result["caption"] == "Check this out"
    assert result["content"] == "Check this out"


def test_parse_malformed_payload():
    """Garbage JSON → all None fields, no crash."""
    result = parse_webhook_payload("whatsapp", {"random": "data"})
    assert result["trigger_type"] is None
    assert result["provider_user_id"] is None
    assert result["content"] is None


def test_parse_status_payload():
    """Status update payload → STATUS_UPDATE trigger."""
    payload = _whatsapp_status_payload("wamid.123", "delivered")
    result = parse_webhook_payload("whatsapp", payload)

    assert result["trigger_type"] == "STATUS_UPDATE"
    assert result["statuses"] is not None
    assert len(result["statuses"]) == 1
    assert result["statuses"][0]["status"] == "delivered"


# ── Test 3: Status Webhook Processing ────────────────────────────────────


@pytest.mark.asyncio
async def test_status_webhook_delivered(db_session: AsyncSession):
    """Delivery receipt updates Message.delivered_at."""
    from app.workers.tasks import _process_status_updates

    user, ws, _ = await _setup_workspace(db_session)

    contact = Contact(workspace_id=ws.id, first_name="Statusee")
    db_session.add(contact)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Hello",
        platform="whatsapp", delivery_status=DeliveryStatus.SENT,
        provider_message_id="wamid.status_test_1",
        sent_at=datetime.utcnow(),
    )
    db_session.add(msg)
    await db_session.flush()

    statuses = [{"id": "wamid.status_test_1", "status": "delivered",
                 "timestamp": str(int(datetime.utcnow().timestamp()))}]
    await _process_status_updates(db_session, statuses, ws.id, str(uuid4()))
    await db_session.flush()

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.DELIVERED
    assert msg.delivered_at is not None


@pytest.mark.asyncio
async def test_status_webhook_read(db_session: AsyncSession):
    """Read receipt updates Message.read_at."""
    from app.workers.tasks import _process_status_updates

    user, ws, _ = await _setup_workspace(db_session)

    contact = Contact(workspace_id=ws.id, first_name="Reader")
    db_session.add(contact)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Read me",
        platform="whatsapp", delivery_status=DeliveryStatus.DELIVERED,
        provider_message_id="wamid.status_test_2",
        sent_at=datetime.utcnow(), delivered_at=datetime.utcnow(),
    )
    db_session.add(msg)
    await db_session.flush()

    statuses = [{"id": "wamid.status_test_2", "status": "read",
                 "timestamp": str(int(datetime.utcnow().timestamp()))}]
    await _process_status_updates(db_session, statuses, ws.id, str(uuid4()))
    await db_session.flush()

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.READ
    assert msg.read_at is not None


@pytest.mark.asyncio
async def test_status_no_regression(db_session: AsyncSession):
    """READ message can't regress to DELIVERED."""
    from app.workers.tasks import _process_status_updates

    user, ws, _ = await _setup_workspace(db_session)

    contact = Contact(workspace_id=ws.id, first_name="NoRegress")
    db_session.add(contact)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Already read",
        platform="whatsapp", delivery_status=DeliveryStatus.READ,
        provider_message_id="wamid.status_test_3",
        sent_at=datetime.utcnow(), delivered_at=datetime.utcnow(),
        read_at=datetime.utcnow(),
    )
    db_session.add(msg)
    await db_session.flush()

    statuses = [{"id": "wamid.status_test_3", "status": "delivered",
                 "timestamp": str(int(datetime.utcnow().timestamp()))}]
    await _process_status_updates(db_session, statuses, ws.id, str(uuid4()))
    await db_session.flush()

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.READ  # Not regressed


# ── Test 4: Phone Normalization ──────────────────────────────────────────


def test_normalize_phone_strips_plus():
    """"+14155551234" → "14155551234"."""
    assert normalize_phone("+14155551234") == "14155551234"


def test_normalize_phone_strips_spaces():
    """"1 415 555 1234" → "14155551234"."""
    assert normalize_phone("1 415 555 1234") == "14155551234"


def test_normalize_phone_strips_all_formatting():
    """"+1 (415) 555-1234" → "14155551234"."""
    assert normalize_phone("+1 (415) 555-1234") == "14155551234"


def test_normalize_phone_digits_unchanged():
    """Already digits-only → unchanged."""
    assert normalize_phone("14155551234") == "14155551234"


@pytest.mark.asyncio
async def test_normalize_consistent_lookup(db_session: AsyncSession):
    """Same phone in different formats → same Contact via resolve_or_create_contact."""
    from app.domain.contacts import resolve_or_create_contact

    _, ws, _ = await _setup_workspace(db_session)

    # First call with raw format
    c1, id1, conv1 = await resolve_or_create_contact(
        db_session, ws.id, "whatsapp", "+1 415 555 9999", first_name="Alice"
    )
    await db_session.flush()

    # Second call with different format → should resolve to same contact
    c2, id2, conv2 = await resolve_or_create_contact(
        db_session, ws.id, "whatsapp", "14155559999", first_name="Alice"
    )
    await db_session.flush()

    assert c1.id == c2.id
    assert id1.id == id2.id


# ── Test 5: Dispatch + Dead Letter ──────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_permanent_failure_dead_letters(db_session: AsyncSession):
    """PERMANENT_FAILURE → DEAD_LETTER status."""
    from app.services.dispatch_service import DispatchService

    user, ws, integration = await _setup_workspace(db_session)

    contact = Contact(workspace_id=ws.id, first_name="DL")
    db_session.add(contact)
    await db_session.flush()

    identity = ChannelIdentity(contact_id=contact.id, provider="whatsapp", provider_user_id="14155550001")
    db_session.add(identity)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Will fail permanently",
        platform="whatsapp", delivery_status=DeliveryStatus.PENDING,
    )
    db_session.add(msg)
    await db_session.flush()

    with patch("app.services.dispatch_service.WhatsAppAdapter") as MockAdapter:
        mock_instance = AsyncMock()
        mock_instance.send_text.side_effect = Exception("PERMANENT_FAILURE: Invalid number (Code: 131030)")
        MockAdapter.return_value = mock_instance

        with pytest.raises(Exception, match="PERMANENT_FAILURE"):
            await DispatchService.dispatch_message(db_session, msg)

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.DEAD_LETTER


@pytest.mark.asyncio
async def test_dispatch_max_retries_dead_letters(db_session: AsyncSession):
    """5 transient failures → DEAD_LETTER."""
    from app.services.dispatch_service import DispatchService

    user, ws, integration = await _setup_workspace(db_session)

    contact = Contact(workspace_id=ws.id, first_name="MaxRetry")
    db_session.add(contact)
    await db_session.flush()

    identity = ChannelIdentity(contact_id=contact.id, provider="whatsapp", provider_user_id="14155550002")
    db_session.add(identity)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Will fail 5 times",
        platform="whatsapp", delivery_status=DeliveryStatus.PENDING,
        attempt_count=4,  # Already 4 attempts, next will be 5th
    )
    db_session.add(msg)
    await db_session.flush()

    with patch("app.services.dispatch_service.WhatsAppAdapter") as MockAdapter:
        mock_instance = AsyncMock()
        mock_instance.send_text.side_effect = Exception("TRANSIENT_FAILURE: Server error (Code: 500)")
        MockAdapter.return_value = mock_instance

        with pytest.raises(Exception, match="TRANSIENT_FAILURE"):
            await DispatchService.dispatch_message(db_session, msg)

    await db_session.refresh(msg)
    assert msg.delivery_status == DeliveryStatus.DEAD_LETTER
    assert msg.attempt_count == 5


@pytest.mark.asyncio
async def test_dead_letter_retry_resets(async_client: AsyncClient, db_session: AsyncSession):
    """POST retry endpoint → resets to PENDING."""
    user, ws, _ = await _setup_workspace(db_session)
    user.is_superuser = False
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(user.id)

    contact = Contact(workspace_id=ws.id, first_name="RetryMe")
    db_session.add(contact)
    await db_session.flush()

    conv = Conversation(workspace_id=ws.id, contact_id=contact.id)
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        workspace_id=ws.id, conversation_id=conv.id,
        direction="outbound", content="Dead letter",
        platform="whatsapp", delivery_status=DeliveryStatus.DEAD_LETTER,
        attempt_count=5, last_error="PERMANENT_FAILURE: test",
    )
    db_session.add(msg)
    await db_session.flush()

    with patch("app.api.v1.inbox.dispatch_message_task") as mock_dispatch:
        r = await async_client.post(
            f"/api/v1/inbox/dead-letter/{msg.id}/retry",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Workspace-ID": str(ws.id),
            },
        )

    assert r.status_code == 200
    d = r.json()
    assert d["success"] is True
    assert d["data"]["status"] == "pending"


# ── Test 6: Payload Size Limit ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_oversized_payload_rejected(async_client: AsyncClient, db_session: AsyncSession):
    """Payload > 1MB → 413."""
    await _setup_workspace(db_session)
    # Create a payload just over 1MB
    oversized = b"x" * (1_048_576 + 1)

    r = await async_client.post(
        "/api/v1/webhooks/whatsapp",
        content=oversized,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413


# ── Test 7: Metrics Service ─────────────────────────────────────────────


def test_metrics_increment_and_get():
    """Metrics counter increments and returns counts."""
    from app.services.metrics_service import MetricsService
    m = MetricsService()
    m.increment("test_counter")
    m.increment("test_counter")
    m.increment("test_labeled", labels={"provider": "whatsapp"})

    counts = m.get_counts()
    assert counts["test_counter"] == 2
    assert counts["test_labeled{provider=whatsapp}"] == 1


def test_metrics_reset():
    """Metrics reset clears all counters."""
    from app.services.metrics_service import MetricsService
    m = MetricsService()
    m.increment("x")
    m.reset()
    assert m.get_counts() == {}
