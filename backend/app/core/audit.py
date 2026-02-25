import logging
import copy
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AdminAuditLog

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"password", "token", "secret", "key", "authorization", "api_key", "cookie", "idempotency_key"}

def redact_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Redacts sensitive keys from a dictionary before saving it to the audit log."""
    if not metadata:
        return {}
    
    redacted = copy.deepcopy(metadata)
    def _redact(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if any(sec in str(k).lower() for sec in SENSITIVE_KEYS):
                    data[k] = "***REDACTED***"
                elif isinstance(v, (dict, list)):
                    _redact(v)
        elif isinstance(data, list):
            for item in data:
                _redact(item)
    _redact(redacted)
    return redacted

async def log_admin_action(
    db: AsyncSession,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    workspace_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[UUID] = None
):
    """
    Records an administrative action in the AdminAuditLog.
    """
    try:
        safe_metadata = redact_metadata(metadata) if metadata else None
        audit_log = AdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            workspace_id=workspace_id,
            metadata_json=safe_metadata,
            correlation_id=correlation_id
        )
        db.add(audit_log)
        # We don't commit here; we let the outer transaction handle it.
    except Exception as e:
        logger.error(f"Failed to assemble AdminAuditLog: {e}")
