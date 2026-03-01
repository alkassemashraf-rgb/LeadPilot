from typing import List, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, Integration, IntegrationStatus, User
from app.schemas.integration import IntegrationRead, IntegrationConnect
from sqlalchemy.exc import IntegrityError
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.security import encrypt_data, decrypt_data
from app.api.deps import require_email_state
from app.core.modules import require_module_enabled, MODULE_INTEGRATIONS_CONNECT
from app.core.catalog_registry import VALID_PROVIDERS
from app.services.entitlements import require_entitlement
from app.services.audit_service import audit_event

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[List[IntegrationRead]], dependencies=[Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "read")), Depends(require_entitlement("integrations_connect"))])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Get all integrations and their statuses for the workspace."""
    result = await db.execute(
        select(Integration).where(Integration.workspace_id == workspace.id)
    )
    integrations = result.scalars().all()
    return wrap_data(integrations)

@router.post("/{provider}/connect", response_model=ResponseEnvelope[IntegrationRead], dependencies=[Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "write")), Depends(require_entitlement("integrations_connect", increment=True))])
async def connect_integration(
    provider: str,
    connect_in: IntegrationConnect,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _allowed: User = Depends(require_email_state("integrations_connect")),
) -> Any:
    """Connect/update an integration (Zoho, WhatsApp, Meta).
    Policy: allowed if verified OR within 7-day verification grace window.
    """
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    # 1. Validation for provider-specific fields
    if "access_token" not in connect_in.config:
        return wrap_error("Missing access_token in config")

    # WhatsApp standard: provider_workspace_id = phone_number_id
    if provider == "whatsapp" and not connect_in.provider_workspace_id:
        return wrap_error("phone_number_id is required for WhatsApp")

    # Meta standard: provider_workspace_id = page_id
    if provider == "meta" and not connect_in.provider_workspace_id:
        return wrap_error("page_id is required for Meta")

    # Zoho standard: provider_workspace_id = org_id (optional but recommended)
    # We enforce NOT NULL for any CONNECTED status below
    if not connect_in.provider_workspace_id:
        return wrap_error(f"Identifier (provider_workspace_id) is required for {provider} connection")

    # 2. Encrypt the config
    encrypted_config = encrypt_data(connect_in.config)

    # 3. Find existing or create new
    result = await db.execute(
        select(Integration).where(
            Integration.workspace_id == workspace.id,
            Integration.provider == provider
        )
    )
    integration = result.scalars().first()

    if not integration:
        integration = Integration(
            workspace_id=workspace.id,
            provider=provider
        )
        db.add(integration)

    integration.status = IntegrationStatus.CONNECTED
    integration.encrypted_config = encrypted_config
    integration.provider_workspace_id = connect_in.provider_workspace_id
    integration.connected_at = datetime.utcnow()
    integration.last_checked_at = datetime.utcnow()
    integration.last_error = None

    try:
        await db.commit()
        await db.refresh(integration)
    except IntegrityError:
        await db.rollback()
        return wrap_error(
            f"This connection ({connect_in.provider_workspace_id}) is already linked to another workspace."
        )

    await audit_event(
        db, action="integration_connect", entity_type="integration",
        entity_id=str(integration.id), actor_user_id=_allowed.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"provider": provider},
    )
    await db.commit()
    await db.refresh(integration)
    return wrap_data(integration)

@router.post("/{provider}/disconnect", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "write")), Depends(require_entitlement("integrations_connect"))])
async def disconnect_integration(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Disconnect and clear integration record."""
    result = await db.execute(
        select(Integration).where(
            Integration.workspace_id == workspace.id,
            Integration.provider == provider
        )
    )
    integration = result.scalars().first()

    if integration:
        integration.status = IntegrationStatus.DISCONNECTED
        integration.provider_workspace_id = None
        integration.encrypted_config = None
        integration.connected_at = None
        integration.last_error = None
        integration.last_checked_at = datetime.utcnow()
        await db.commit()

    await audit_event(
        db, action="integration_disconnect", entity_type="integration",
        entity_id=str(integration.id) if integration else provider,
        actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"provider": provider},
    )
    await db.commit()
    return wrap_data({"message": f"{provider} disconnected successfully"})

@router.post("/health-check", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "read")), Depends(require_entitlement("integrations_connect"))])
async def integrations_health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Perform structural validation for all connected integrations."""
    result = await db.execute(
        select(Integration).where(Integration.workspace_id == workspace.id)
    )
    integrations = result.scalars().all()
    
    errors_found = 0
    for integration in integrations:
        integration.last_checked_at = datetime.utcnow()
        if integration.status == IntegrationStatus.CONNECTED:
            # Structural validation
            if not integration.provider_workspace_id or not integration.encrypted_config:
                integration.status = IntegrationStatus.ERROR
                integration.last_error = "Missing structural configuration (provider_workspace_id or encrypted_config)"
                errors_found += 1
            else:
                try:
                    # Attempt decryption as sanity check
                    decrypt_data(integration.encrypted_config)
                except Exception as e:
                    integration.status = IntegrationStatus.ERROR
                    integration.last_error = f"Configuration decryption failed: {str(e)}"
                    errors_found += 1
        
        db.add(integration)

    await audit_event(
        db, action="integration_health_check", entity_type="workspace",
        entity_id=str(workspace.id), actor_user_id=current_user.id,
        outcome="success", workspace_id=workspace.id, request=request,
        metadata={"checked_count": len(integrations), "errors_found": errors_found},
    )
    await db.commit()
    return wrap_data({"status": "ok", "checked_count": len(integrations), "errors_found": errors_found})

@router.post("/meta/webhooks/subscribe", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "write")), Depends(require_entitlement("integrations_connect"))])
async def subscribe_meta_webhooks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Manually trigger webhook subscription for a connected Meta integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.workspace_id == workspace.id,
            Integration.provider == "meta",
            Integration.status == IntegrationStatus.CONNECTED,
        )
    )
    integration = result.scalars().first()
    if not integration or not integration.encrypted_config:
        return wrap_error("No connected Meta integration found")

    config = decrypt_data(integration.encrypted_config)
    page_id = integration.provider_workspace_id
    page_access_token = config.get("access_token")

    from app.services.meta_service import subscribe_page_webhooks
    success = await subscribe_page_webhooks(page_id, page_access_token)

    await audit_event(
        db, action="meta_webhook_subscribe", entity_type="integration",
        entity_id=str(integration.id), actor_user_id=current_user.id,
        outcome="success" if success else "failure",
        workspace_id=workspace.id, request=request,
        metadata={"provider": "meta", "page_id": page_id},
    )
    await db.commit()

    if success:
        return wrap_data({"message": "Webhook subscription successful", "page_id": page_id})
    return wrap_error("Failed to subscribe to webhooks")
