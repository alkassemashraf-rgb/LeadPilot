"""Universal OAuth provider routes — authorize, callback, connections CRUD."""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api import deps
from app.core.config import settings
from app.core.db import get_db
from app.models.models import OAuthConnection, OAuthConnectionStatus, User, Workspace, WorkspaceRole
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.schemas.oauth import OAuthAuthorizeResponse, OAuthConnectionRead
from app.services import oauth_service
from app.services.audit_service import audit_event
from app.services.oauth_providers import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter()


def _redirect_uri(provider_code: str, request: Request) -> str:
    base = settings.APP_BASE_URL or str(request.base_url).rstrip("/")
    return f"{base}{settings.API_V1_STR}/oauth/{provider_code}/callback"


# ─── Authorize ────────────────────────────────────────────────────────────────

@router.get(
    "/{provider_code}/authorize",
    response_model=ResponseEnvelope[OAuthAuthorizeResponse],
    summary="Start OAuth flow — returns authorization URL",
)
async def authorize(
    provider_code: str,
    request: Request,
    redirect_after: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    workspace: Optional[Workspace] = Depends(deps.get_active_workspace),
):
    """
    Generate the provider authorization URL. The client should redirect the browser to it.
    Requires X-Workspace-ID header.
    RBAC: workspace Owner or Member (not Viewer).
    """
    # RBAC: Viewers cannot connect integrations
    membership = await _get_membership(db, current_user.id, workspace.id)
    if membership.role == WorkspaceRole.VIEWER:
        return wrap_error("Viewers cannot connect OAuth integrations")

    try:
        provider = await oauth_service.get_provider(db, provider_code)
        client_id, _ = oauth_service._get_credentials(provider_code)
    except Exception as e:
        return wrap_error(str(e))

    state = await oauth_service.create_oauth_state(
        db,
        provider_code=provider_code,
        workspace_id=workspace.id,
        user_id=current_user.id,
        redirect_after=redirect_after,
    )
    await db.commit()

    adapter = get_adapter(provider_code)
    redirect_uri = _redirect_uri(provider_code, request)
    auth_url = oauth_service.build_authorization_url(
        provider=provider,
        adapter=adapter,
        state_token=state.state_token,
        redirect_uri=redirect_uri,
        client_id=client_id,
    )

    await audit_event(
        db,
        action="oauth.authorize.started",
        entity_type="oauth_provider",
        entity_id=provider_code,
        actor_user_id=current_user.id,
        outcome="success",
        workspace_id=workspace.id,
        request=request,
        metadata={"provider_code": provider_code},
    )
    await db.commit()

    return wrap_data({"authorization_url": auth_url})


# ─── Callback ─────────────────────────────────────────────────────────────────

@router.get(
    "/{provider_code}/callback",
    summary="OAuth callback — exchanges code for token, saves connection, redirects to frontend",
    include_in_schema=True,
)
async def callback(
    provider_code: str,
    request: Request,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Provider redirects here after user authorization.
    No auth header — this is a browser redirect from the OAuth provider.
    On success: redirect to {FRONTEND_URL}/integrations/callback?status=success&provider={code}
    On failure: redirect to {FRONTEND_URL}/integrations/callback?status=error&provider={code}&reason={msg}
    """
    frontend_base = settings.FRONTEND_URL

    def _error_redirect(reason: str) -> RedirectResponse:
        return RedirectResponse(
            f"{frontend_base}/integrations/callback?status=error&provider={provider_code}&reason={reason}"
        )

    if error or not code or not state:
        return _error_redirect(error or "missing_params")

    # Validate state
    try:
        oauth_state = await oauth_service.validate_and_consume_state(db, state)
    except Exception:
        await db.rollback()
        return _error_redirect("invalid_state")

    # Exchange code for token
    try:
        provider = await oauth_service.get_provider(db, provider_code)
        adapter = get_adapter(provider_code)
        client_id, client_secret = oauth_service._get_credentials(provider_code)
        redirect_uri = _redirect_uri(provider_code, request)

        token_data = await oauth_service.exchange_code_for_token(
            provider=provider,
            adapter=adapter,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as e:
        logger.exception(f"OAuth token exchange failed for {provider_code}: {e}")
        try:
            await audit_event(
                db,
                action="oauth.callback.failed",
                entity_type="oauth_provider",
                entity_id=provider_code,
                actor_type="service",
                outcome="failure",
                workspace_id=oauth_state.workspace_id,
                request=request,
                error_message=str(e),
                metadata={"provider_code": provider_code},
            )
            await db.commit()
        except Exception:
            pass
        return _error_redirect("token_exchange_failed")

    # Save connection
    try:
        conn = await oauth_service.save_connection(
            db=db,
            provider_code=provider_code,
            workspace_id=oauth_state.workspace_id,
            user_id=oauth_state.user_id,
            token_data=token_data,
            adapter=adapter,
        )

        await audit_event(
            db,
            action="oauth.callback.success",
            entity_type="oauth_connection",
            entity_id=str(conn.id),
            actor_user_id=oauth_state.user_id,
            actor_type="user",
            outcome="success",
            workspace_id=oauth_state.workspace_id,
            request=request,
            metadata={
                "provider_code": provider_code,
                "external_account_id": conn.external_account_id,
                "external_account_name": conn.external_account_name,
            },
        )
        await db.commit()
    except Exception as e:
        logger.exception(f"OAuth save_connection failed for {provider_code}: {e}")
        await db.rollback()
        return _error_redirect("save_failed")

    redirect_after = oauth_state.redirect_after or "/integrations"
    return RedirectResponse(
        f"{frontend_base}/integrations/callback?status=success&provider={provider_code}"
        f"&redirect_after={redirect_after}"
    )


# ─── List Connections ──────────────────────────────────────────────────────────

@router.get(
    "/connections",
    response_model=ResponseEnvelope[List[OAuthConnectionRead]],
    summary="List active OAuth connections for this workspace",
)
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
):
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.workspace_id == workspace.id,
            OAuthConnection.status != OAuthConnectionStatus.REVOKED,
        )
    )
    conns = result.scalars().all()
    return wrap_data([OAuthConnectionRead.model_validate(c) for c in conns])


# ─── Disconnect ────────────────────────────────────────────────────────────────

@router.delete(
    "/connections/{connection_id}",
    response_model=ResponseEnvelope[OAuthConnectionRead],
    summary="Revoke / disconnect an OAuth connection",
)
async def disconnect(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
):
    # RBAC: owner or member only
    membership = await _get_membership(db, current_user.id, workspace.id)
    if membership.role == WorkspaceRole.VIEWER:
        return wrap_error("Viewers cannot disconnect OAuth integrations")

    # Confirm connection belongs to this workspace
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.id == connection_id,
            OAuthConnection.workspace_id == workspace.id,
        )
    )
    conn = result.scalars().first()
    if not conn:
        return wrap_error("OAuth connection not found")

    conn = await oauth_service.revoke_connection(db, connection_id)
    await db.commit()
    return wrap_data(OAuthConnectionRead.model_validate(conn))


# ─── Manual Refresh ────────────────────────────────────────────────────────────

@router.post(
    "/connections/{connection_id}/refresh",
    response_model=ResponseEnvelope[OAuthConnectionRead],
    summary="Manually refresh the access token for a connection",
)
async def refresh_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
    workspace: Workspace = Depends(deps.get_active_workspace),
):
    # RBAC: owner only
    membership = await _get_membership(db, current_user.id, workspace.id)
    if membership.role != WorkspaceRole.OWNER:
        return wrap_error("Only workspace owners can refresh OAuth tokens")

    # Confirm connection belongs to this workspace
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.id == connection_id,
            OAuthConnection.workspace_id == workspace.id,
        )
    )
    if not result.scalars().first():
        return wrap_error("OAuth connection not found")

    try:
        conn = await oauth_service.refresh_access_token(db, connection_id)
        await db.commit()
        return wrap_data(OAuthConnectionRead.model_validate(conn))
    except Exception as e:
        return wrap_error(str(e))


# ─── Helpers ───────────────────────────────────────────────────────────────────

async def _get_membership(db: AsyncSession, user_id: UUID, workspace_id: UUID):
    from app.models.models import WorkspaceMember
    from fastapi import HTTPException
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of this workspace")
    return membership
