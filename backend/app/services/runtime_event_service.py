import logging
import copy
import re
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import SENSITIVE_KEYS
from app.models.models import RuntimeEventLog

logger = logging.getLogger(__name__)

# Regex patterns for additional scrubbing
_SG_KEY_RE = re.compile(r"SG\.\S+")
_BEARER_RE = re.compile(r"Bearer\s+\S+")

MAX_STRING_LENGTH = 2048
MAX_ARRAY_LENGTH = 20
MAX_DICT_KEYS = 50


def redact_payload(payload: Any) -> Any:
    """
    Deep-redact a payload dict for safe storage.
    - Reuses SENSITIVE_KEYS from app.core.audit
    - Scrubs SG.* SendGrid keys and Bearer tokens
    - Truncates long strings, arrays, and large dicts
    """
    if payload is None:
        return None
    if not isinstance(payload, (dict, list)):
        return payload

    data = copy.deepcopy(payload)
    return _redact(data)


def _redact(data: Any) -> Any:
    if isinstance(data, dict):
        # Cap number of keys
        if len(data) > MAX_DICT_KEYS:
            keys = list(data.keys())[:MAX_DICT_KEYS]
            data = {k: data[k] for k in keys}
            data["_truncated"] = True

        for k in list(data.keys()):
            if any(sec in str(k).lower() for sec in SENSITIVE_KEYS):
                data[k] = "***REDACTED***"
            else:
                data[k] = _redact(data[k])
        return data
    elif isinstance(data, list):
        truncated = len(data) > MAX_ARRAY_LENGTH
        items = [_redact(item) for item in data[:MAX_ARRAY_LENGTH]]
        if truncated:
            items.append({"_truncated": True})
        return items
    elif isinstance(data, str):
        # Scrub SendGrid API keys
        val = _SG_KEY_RE.sub("SG.***", data)
        # Scrub Bearer tokens
        val = _BEARER_RE.sub("Bearer ***", val)
        # Truncate long strings
        if len(val) > MAX_STRING_LENGTH:
            val = val[:MAX_STRING_LENGTH] + "...[truncated]"
        return val
    return data


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    source: str,
    workspace_id: Optional[UUID] = None,
    correlation_id: Optional[str] = None,
    related_ids: Optional[Dict[str, Any]] = None,
    actor_user_id: Optional[UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
    outcome: str = "success",
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
):
    """
    Non-throwing runtime event logger.
    Adds to session but does NOT commit — caller commits.
    """
    try:
        safe_payload = redact_payload(payload) if payload else None
        safe_error = error_message[:MAX_STRING_LENGTH] if error_message and len(error_message) > MAX_STRING_LENGTH else error_message

        # Coerce string UUIDs to UUID objects for SQLAlchemy compatibility
        ws_id = UUID(str(workspace_id)) if workspace_id and not isinstance(workspace_id, UUID) else workspace_id
        actor_id = UUID(str(actor_user_id)) if actor_user_id and not isinstance(actor_user_id, UUID) else actor_user_id

        event = RuntimeEventLog(
            workspace_id=ws_id,
            event_type=event_type,
            source=source,
            correlation_id=str(correlation_id) if correlation_id else None,
            related_ids=related_ids,
            actor_user_id=actor_id,
            payload=safe_payload,
            outcome=outcome,
            error_message=safe_error,
            duration_ms=duration_ms,
        )
        db.add(event)
        await db.flush()
    except Exception as e:
        logger.warning(f"Failed to log runtime event ({event_type}): {e}")
        try:
            await db.rollback()
        except Exception:
            pass
