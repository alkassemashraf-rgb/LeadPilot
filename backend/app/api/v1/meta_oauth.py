"""Meta OAuth 2.0 connect flow — start and callback endpoints."""
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api import deps
from app.core.config import settings
from app.core.db import get_db
from app.core.modules import require_module_enabled, MODULE_INTEGRATIONS_CONNECT
from app.core.security import encrypt_data
from app.models.models import Integration, IntegrationStatus, User, Workspace
from app.schemas.envelope import wrap_data, wrap_error
from app.services.audit_service import audit_event
from app.services.entitlements import require_entitlement
from app.services.meta_service import subscribe_page_webhooks
from app.services.metrics_service import metrics
from app.services.runtime_event_service import log_event

logger = logging.getLogger(__name__)
router = APIRouter()

GRAPH_API_VERSION = "v18.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
META_SCOPES = "pages_messaging,pages_manage_metadata,instagram_manage_messages,leads_retrieval,pages_read_engagement"


@router.get(
    "/start",
    dependencies=[
        Depends(require_module_enabled(MODULE_INTEGRATIONS_CONNECT, "write")),
        Depends(require_entitlement("integrations_connect")),
    ],
)
async def meta_oauth_start(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    current_user: User = Depends(deps.get_current_user),
):
    """Build Meta authorization URL and return it."""
    if not settings.META_CLIENT_ID or not settings.META_CLIENT_SECRET:
        return wrap_error("META_CLIENT_ID and META_CLIENT_SECRET must be configured")

    redirect_uri = settings.META_OAUTH_REDIRECT_URI
    if not redirect_uri:
        base = settings.APP_BASE_URL or settings.FRONTEND_URL
        redirect_uri = f"{base}/api/v1/integrations/meta/oauth/callback"

    # Encode workspace + user into JWT state param (10-min expiry)
    state_payload = {
        "sub": str(current_user.id),
        "workspace_id": str(workspace.id),
        "exp": datetime.utcnow() + timedelta(minutes=10),
        "purpose": "meta_oauth",
    }
    state_token = jwt.encode(
        state_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    params = {
        "client_id": settings.META_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": META_SCOPES,
        "state": state_token,
        "response_type": "code",
    }
    auth_url = f"https://www.facebook.com/{GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"

    metrics.increment("meta_oauth_started")
    await log_event(
        db, event_type="meta.oauth.started", source="meta_oauth",
        workspace_id=workspace.id,
    )
    await db.commit()

    return wrap_data({"auth_url": auth_url})


@router.get("/callback")
async def meta_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange authorization code for token, subscribe webhooks, store integration."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    frontend_base = settings.FRONTEND_URL

    if error or not code or not state:
        metrics.increment("meta_oauth_failed")
        return RedirectResponse(
            f"{frontend_base}/settings/integrations?oauth=meta&status=error&reason={error or 'missing_params'}"
        )

    # Decode state JWT
    try:
        state_data = jwt.decode(
            state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if state_data.get("purpose") != "meta_oauth":
            raise JWTError("Invalid state purpose")
        user_id = state_data["sub"]
        workspace_id = state_data["workspace_id"]
    except JWTError:
        metrics.increment("meta_oauth_failed")
        return RedirectResponse(
            f"{frontend_base}/settings/integrations?oauth=meta&status=error&reason=invalid_state"
        )

    redirect_uri = settings.META_OAUTH_REDIRECT_URI
    if not redirect_uri:
        base = settings.APP_BASE_URL or settings.FRONTEND_URL
        redirect_uri = f"{base}/api/v1/integrations/meta/oauth/callback"

    try:
        async with httpx.AsyncClient() as client:
            # 1. Exchange code for short-lived user token
            token_resp = await client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={
                    "client_id": settings.META_CLIENT_ID,
                    "redirect_uri": redirect_uri,
                    "client_secret": settings.META_CLIENT_SECRET,
                    "code": code,
                },
            )
            if token_resp.status_code != 200:
                raise Exception(f"Token exchange failed: {token_resp.text}")
            short_token = token_resp.json().get("access_token")

            # 2. Exchange for long-lived token
            ll_resp = await client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_CLIENT_ID,
                    "client_secret": settings.META_CLIENT_SECRET,
                    "fb_exchange_token": short_token,
                },
            )
            if ll_resp.status_code != 200:
                raise Exception(f"Long-lived token exchange failed: {ll_resp.text}")
            long_lived_user_token = ll_resp.json().get("access_token")

            # 3. Fetch pages
            pages_resp = await client.get(
                f"{GRAPH_BASE}/me/accounts",
                params={"access_token": long_lived_user_token},
            )
            if pages_resp.status_code != 200:
                raise Exception(f"Page fetch failed: {pages_resp.text}")
            pages = pages_resp.json().get("data", [])
            if not pages:
                raise Exception("No pages found for this user")

            page = pages[0]
            page_id = page["id"]
            page_access_token = page["access_token"]
            page_name = page.get("name", "")

            # 4. Fetch Instagram Business Account (optional)
            ig_account_id = None
            try:
                ig_resp = await client.get(
                    f"{GRAPH_BASE}/{page_id}",
                    params={
                        "fields": "instagram_business_account",
                        "access_token": page_access_token,
                    },
                )
                if ig_resp.status_code == 200:
                    ig_data = ig_resp.json().get("instagram_business_account", {})
                    ig_account_id = ig_data.get("id")
            except Exception:
                logger.warning("Could not fetch Instagram Business Account ID")

            # 5. Subscribe webhooks
            await subscribe_page_webhooks(page_id, page_access_token)

        # 6. Store Integration
        config_data = {
            "access_token": page_access_token,
            "page_name": page_name,
            "instagram_business_account_id": ig_account_id,
        }
        encrypted_config = encrypt_data(config_data)

        from uuid import UUID
        ws_id = UUID(workspace_id)

        result = await db.execute(
            select(Integration).where(
                Integration.workspace_id == ws_id,
                Integration.provider == "meta",
            )
        )
        integration = result.scalars().first()

        if not integration:
            integration = Integration(workspace_id=ws_id, provider="meta")
            db.add(integration)

        integration.status = IntegrationStatus.CONNECTED
        integration.encrypted_config = encrypted_config
        integration.provider_workspace_id = page_id
        integration.connected_at = datetime.utcnow()
        integration.last_checked_at = datetime.utcnow()
        integration.last_error = None

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            metrics.increment("meta_oauth_failed")
            return RedirectResponse(
                f"{frontend_base}/settings/integrations?oauth=meta&status=error&reason=page_already_linked"
            )

        await audit_event(
            db, action="integration_connect", entity_type="integration",
            entity_id=str(integration.id), actor_user_id=UUID(user_id),
            outcome="success", workspace_id=ws_id, request=request,
            metadata={"provider": "meta", "method": "oauth", "page_name": page_name},
        )
        await db.commit()

        metrics.increment("meta_oauth_completed")
        await log_event(
            db, event_type="meta.oauth.completed", source="meta_oauth",
            workspace_id=ws_id,
            payload={"page_id": page_id, "page_name": page_name},
        )
        await db.commit()

        return RedirectResponse(
            f"{frontend_base}/settings/integrations?oauth=meta&status=success"
        )

    except Exception as e:
        logger.exception(f"Meta OAuth callback error: {e}")
        metrics.increment("meta_oauth_failed")
        try:
            await log_event(
                db, event_type="meta.oauth.failed", source="meta_oauth",
                outcome="failure", error_message=str(e),
            )
            await db.commit()
        except Exception:
            pass
        return RedirectResponse(
            f"{frontend_base}/settings/integrations?oauth=meta&status=error&reason=callback_error"
        )
