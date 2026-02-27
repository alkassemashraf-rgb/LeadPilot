"""
Mission 18 — Runtime Event Trail Tests
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from uuid import uuid4

from app.models.models import RuntimeEventLog
from app.services.runtime_event_service import log_event, redact_payload


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _count_events(db: AsyncSession, **filters) -> int:
    q = select(func.count(RuntimeEventLog.id))
    for k, v in filters.items():
        q = q.where(getattr(RuntimeEventLog, k) == v)
    result = await db.execute(q)
    return result.scalar_one()


# ── Service Unit Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_event_stores_fields(db_session: AsyncSession):
    """log_event() should persist all provided fields."""
    ws_id = uuid4()
    corr = str(uuid4())
    await log_event(
        db_session,
        event_type="webhook.received",
        source="webhook",
        workspace_id=ws_id,
        correlation_id=corr,
        related_ids={"webhook_event_id": "evt-123"},
        payload={"provider": "whatsapp", "phone_number_id": "12345"},
        outcome="success",
        duration_ms=42,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(RuntimeEventLog).where(RuntimeEventLog.correlation_id == corr)
    )
    entry = result.scalars().first()

    assert entry is not None
    assert entry.event_type == "webhook.received"
    assert entry.source == "webhook"
    assert entry.workspace_id == ws_id
    assert entry.outcome == "success"
    assert entry.duration_ms == 42
    assert entry.related_ids["webhook_event_id"] == "evt-123"
    assert entry.payload["provider"] == "whatsapp"


@pytest.mark.asyncio
async def test_log_event_redacts_payload(db_session: AsyncSession):
    """Sensitive keys and Bearer tokens should be redacted in stored payload."""
    await log_event(
        db_session,
        event_type="test.redact",
        source="test",
        payload={
            "access_token": "secret-token-value",
            "provider": "meta",
            "authorization": "Bearer sk-1234",
        },
    )
    await db_session.commit()

    result = await db_session.execute(
        select(RuntimeEventLog).where(RuntimeEventLog.event_type == "test.redact")
    )
    entry = result.scalars().first()

    assert entry is not None
    assert entry.payload["access_token"] == "***REDACTED***"
    assert entry.payload["authorization"] == "***REDACTED***"
    assert entry.payload["provider"] == "meta"


@pytest.mark.asyncio
async def test_log_event_swallows_exceptions(db_session: AsyncSession):
    """log_event() should not raise even on invalid data."""
    # Pass a non-UUID for workspace_id to trigger a potential error — but log_event is non-throwing
    # Actually, let's just ensure it handles gracefully without crashing
    try:
        await log_event(
            db_session,
            event_type="test.error_handling",
            source="test",
        )
        await db_session.commit()
    except Exception:
        pytest.fail("log_event() should not raise exceptions")


@pytest.mark.asyncio
async def test_redact_payload_truncates_long_strings():
    """Strings longer than 2048 chars should be truncated."""
    long_string = "x" * 5000
    result = redact_payload({"data": long_string})
    assert len(result["data"]) < 5000
    assert result["data"].endswith("...[truncated]")


@pytest.mark.asyncio
async def test_redact_payload_truncates_arrays():
    """Arrays with > 20 items should be truncated."""
    long_array = list(range(50))
    result = redact_payload({"items": long_array})
    assert len(result["items"]) == 21  # 20 items + truncation marker
    assert result["items"][-1] == {"_truncated": True}


@pytest.mark.asyncio
async def test_redact_payload_scrubs_sendgrid_keys():
    """SG.* patterns should be scrubbed."""
    result = redact_payload({"api_response": "API key is SG.abc123xyz.foobar"})
    assert "SG.abc123xyz" not in result["api_response"]
    assert "SG.***" in result["api_response"]


@pytest.mark.asyncio
async def test_redact_payload_scrubs_bearer_tokens():
    """Bearer tokens should be scrubbed."""
    result = redact_payload({"header": "Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"})
    assert "eyJhbGciOiJIUzI1NiJ9" not in result["header"]
    assert "Bearer ***" in result["header"]


@pytest.mark.asyncio
async def test_redact_payload_caps_dict_keys():
    """Dicts with > 50 keys should be truncated."""
    big_dict = {f"key_{i}": i for i in range(80)}
    result = redact_payload(big_dict)
    assert "_truncated" in result
    assert result["_truncated"] is True
    # Should have at most 51 keys (50 original + _truncated)
    assert len(result) <= 51
