"""
Enterprise Audit Service — Mission 17

Primary API: audit_event()
Backward compat: log_admin_action() in app.core.audit stays untouched.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AdminAuditLog
from app.core.audit import redact_metadata

logger = logging.getLogger(__name__)

_MAX_USER_AGENT = 512
_MAX_ERROR_MSG = 2048


async def audit_event(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: Optional[UUID] = None,
    actor_type: str = "user",
    outcome: str = "success",
    workspace_id: Optional[UUID] = None,
    agency_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    correlation_id: Optional[UUID] = None,
) -> None:
    """
    Record an enterprise audit event.  Non-throwing — catches all errors.
    Does NOT commit; caller must commit the outer transaction.
    """
    try:
        safe_metadata = redact_metadata(metadata) if metadata else None

        ip_address = None
        user_agent = None
        request_path = None
        request_method = None

        if request is not None:
            ip_address = request.client.host if request.client else None
            raw_ua = request.headers.get("user-agent") or ""
            user_agent = raw_ua[:_MAX_USER_AGENT] or None
            request_path = str(request.url.path)
            request_method = request.method
            if correlation_id is None:
                cid = getattr(request.state, "correlation_id", None)
                if cid and isinstance(cid, str):
                    try:
                        correlation_id = UUID(cid)
                    except ValueError:
                        pass

        entry = AdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            workspace_id=workspace_id,
            metadata_json=safe_metadata,
            correlation_id=correlation_id,
            actor_type=actor_type,
            agency_id=agency_id,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            error_code=error_code,
            error_message=(error_message or "")[:_MAX_ERROR_MSG] or None,
        )
        db.add(entry)
    except Exception as e:
        logger.error(f"audit_event failed: {e}")
