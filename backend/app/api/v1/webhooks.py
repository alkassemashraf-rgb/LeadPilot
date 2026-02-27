import hmac
import hashlib
import json
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.exc import IntegrityError

from app.core.db import get_db
from app.core.config import settings
from app.models.models import Integration, WebhookEventLog, WebhookStatus
from app.workers.tasks import process_webhook_event
from app.core.modules import require_module_enabled, MODULE_WEBHOOKS_INGESTION
from app.services.entitlements import require_entitlement
from app.services.runtime_event_service import log_event

router = APIRouter()

def verify_meta_signature(payload: bytes, signature: str, algorithm: str = "sha1") -> bool:
    """Verify HMAC signature from Meta."""
    if not settings.META_APP_SECRET:
        return True # Skip if not configured in MVP
    
    if algorithm == "sha256":
        prefix = "sha256="
        hash_func = hashlib.sha256
    else:
        prefix = "sha1="
        hash_func = hashlib.sha1
        
    if not signature or not signature.startswith(prefix):
        return False
        
    expected_signature = hmac.new(
        settings.META_APP_SECRET.encode(),
        payload,
        hash_func
    ).hexdigest()
    
    return hmac.compare_digest(f"{prefix}{expected_signature}", signature)

async def resolve_workspace(db: AsyncSession, provider: str, provider_workspace_id: str) -> Optional[UUID]:
    """Resolve workspace_id based on provider and its specific ID."""
    result = await db.execute(
        select(Integration).where(
            Integration.provider == provider,
            Integration.provider_workspace_id == provider_workspace_id
        )
    )
    integration = result.scalars().first()
    return integration.workspace_id if integration else None

@router.get("/meta", dependencies=[Depends(require_module_enabled(MODULE_WEBHOOKS_INGESTION, "read"))])
@router.get("/whatsapp", dependencies=[Depends(require_module_enabled(MODULE_WEBHOOKS_INGESTION, "read"))])
async def verify_webhook(request: Request):
    """Generic verification for Meta/WhatsApp (uses query params)."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge)
    
    return Response(content="Verification failed", status_code=403)

@router.post("/whatsapp", dependencies=[Depends(require_module_enabled(MODULE_WEBHOOKS_INGESTION, "write"))])
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Inbound WhatsApp Webhook."""
    payload_bytes = await request.body()
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON"}

    # 1. Extract IDs
    phone_number_id = None
    event_id = None

    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")

        messages = value.get("messages", [])
        if messages:
            event_id = messages[0].get("id")
        else:
            event_id = f"wa_{hashlib.md5(payload_bytes).hexdigest()}"
    except (IndexError, AttributeError):
        pass

    await log_event(db, event_type="webhook.received", source="webhook",
                    payload={"provider": "whatsapp", "phone_number_id": phone_number_id})

    # 2. Resolve Workspace
    workspace_id = await resolve_workspace(db, "whatsapp", phone_number_id) if phone_number_id else None

    if workspace_id:
        await log_event(db, event_type="webhook.workspace_resolved", source="webhook",
                        workspace_id=workspace_id, payload={"provider": "whatsapp"})
    else:
        await log_event(db, event_type="webhook.workspace_not_found", source="webhook",
                        outcome="failure", payload={"provider": "whatsapp", "phone_number_id": phone_number_id})

    # 3. Store Event Log
    correlation_id = uuid4()
    event_log = WebhookEventLog(
        provider="whatsapp",
        provider_event_id=event_id or f"gen_{correlation_id}",
        workspace_id=workspace_id,
        payload=payload,
        correlation_id=correlation_id,
        status=WebhookStatus.RECEIVED
    )

    if not workspace_id:
        event_log.status = WebhookStatus.FAILED
        event_log.last_error = "workspace_not_found"

    try:
        db.add(event_log)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"status": "ok", "message": "duplicate"}

    # 4. Dispatch Task ONLY if resolved
    if workspace_id:
        process_webhook_event.delay(str(event_log.id))
        await log_event(db, event_type="webhook.queued", source="webhook",
                        workspace_id=workspace_id, correlation_id=str(correlation_id),
                        related_ids={"webhook_event_id": str(event_log.id)})
        await db.commit()

    return {"status": "ok", "correlation_id": str(correlation_id)}

@router.post("/meta", dependencies=[Depends(require_module_enabled(MODULE_WEBHOOKS_INGESTION, "write"))])
async def meta_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_hub_signature: str = Header(None, alias="X-Hub-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """Inbound Meta Webhook."""
    payload_bytes = await request.body()

    # 1. Signature Check (SHA-256 preferred, fallback to SHA-1)
    if x_hub_signature_256:
        if not verify_meta_signature(payload_bytes, x_hub_signature_256, algorithm="sha256"):
            if settings.META_APP_SECRET:
                await log_event(db, event_type="webhook.signature_invalid", source="webhook",
                                outcome="failure", payload={"provider": "meta", "algorithm": "sha256"})
                await db.commit()
                raise HTTPException(status_code=403, detail="Invalid SHA-256 signature")
    elif x_hub_signature:
        if not verify_meta_signature(payload_bytes, x_hub_signature, algorithm="sha1"):
            if settings.META_APP_SECRET:
                await log_event(db, event_type="webhook.signature_invalid", source="webhook",
                                outcome="failure", payload={"provider": "meta", "algorithm": "sha1"})
                await db.commit()
                raise HTTPException(status_code=403, detail="Invalid SHA-1 signature")

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON"}

    # 2. Extract IDs
    page_id = None
    event_id = None

    try:
        entry = payload.get("entry", [])[0]
        page_id = entry.get("id")

        messaging = entry.get("messaging", [])
        if messaging:
            event_id = messaging[0].get("message", {}).get("mid")

        changes = entry.get("changes", [])
        if changes:
            event_id = changes[0].get("value", {}).get("leadgen_id")

        if not event_id:
            event_id = f"meta_{hashlib.md5(payload_bytes).hexdigest()}"
    except (IndexError, AttributeError):
        pass

    await log_event(db, event_type="webhook.received", source="webhook",
                    payload={"provider": "meta", "page_id": page_id})

    # 3. Resolve Workspace
    workspace_id = await resolve_workspace(db, "meta", page_id) if page_id else None

    if workspace_id:
        await log_event(db, event_type="webhook.workspace_resolved", source="webhook",
                        workspace_id=workspace_id, payload={"provider": "meta"})
    else:
        await log_event(db, event_type="webhook.workspace_not_found", source="webhook",
                        outcome="failure", payload={"provider": "meta", "page_id": page_id})

    # 4. Store & Dispatch
    correlation_id = uuid4()
    event_log = WebhookEventLog(
        provider="meta",
        provider_event_id=event_id or f"gen_{correlation_id}",
        workspace_id=workspace_id,
        payload=payload,
        correlation_id=correlation_id,
        status=WebhookStatus.RECEIVED
    )

    if not workspace_id:
        event_log.status = WebhookStatus.FAILED
        event_log.last_error = "workspace_not_found"

    try:
        db.add(event_log)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"status": "ok", "message": "duplicate"}

    # Dispatch ONLY if resolved
    if workspace_id:
        process_webhook_event.delay(str(event_log.id))
        await log_event(db, event_type="webhook.queued", source="webhook",
                        workspace_id=workspace_id, correlation_id=str(correlation_id),
                        related_ids={"webhook_event_id": str(event_log.id)})
        await db.commit()

    return {"status": "ok", "correlation_id": str(correlation_id)}
