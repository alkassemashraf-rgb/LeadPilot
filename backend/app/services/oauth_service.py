"""Universal OAuth service. Provider-agnostic lifecycle management for OAuth connections."""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import decrypt_string, encrypt_string
from app.models.models import OAuthConnection, OAuthConnectionStatus, OAuthProvider, OAuthState
from app.services.audit_service import audit_event
from app.services.oauth_providers import BaseOAuthAdapter, get_adapter

logger = logging.getLogger(__name__)

# State token TTL
_STATE_TTL_MINUTES = 10


async def get_provider(db: AsyncSession, provider_code: str) -> OAuthProvider:
    """Load an active provider by code. Raises 404 if missing or inactive."""
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.provider_code == provider_code)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OAuth provider '{provider_code}' not found")
    if not provider.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth provider '{provider_code}' is disabled")
    return provider


async def create_oauth_state(
    db: AsyncSession,
    provider_code: str,
    workspace_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    redirect_after: Optional[str] = None,
    purpose: str = "integration",
) -> OAuthState:
    """Generate a secure CSRF state token and persist it with a 10-minute TTL.

    purpose: "integration" (default) for workspace OAuth connections,
             "social_auth" for user authentication flows.
    """
    state_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=_STATE_TTL_MINUTES)
    state = OAuthState(
        provider_code=provider_code,
        state_token=state_token,
        workspace_id=workspace_id,
        user_id=user_id,
        redirect_after=redirect_after,
        purpose=purpose,
        expires_at=expires_at,
    )
    db.add(state)
    await db.flush()
    return state


async def validate_and_consume_state(db: AsyncSession, state_token: str) -> OAuthState:
    """Validate state token (exists + not expired) and delete it (one-time use)."""
    result = await db.execute(
        select(OAuthState).where(OAuthState.state_token == state_token)
    )
    state = result.scalars().first()
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state token")
    if state.expires_at < datetime.utcnow():
        await db.delete(state)
        await db.flush()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state token has expired")
    await db.delete(state)
    await db.flush()
    return state


def build_authorization_url(
    provider: OAuthProvider,
    adapter: BaseOAuthAdapter,
    state_token: str,
    redirect_uri: str,
    client_id: str,
) -> str:
    """Build the provider authorization URL using the adapter."""
    import json
    scopes: list[str] = []
    if provider.scopes_json:
        try:
            scopes = json.loads(provider.scopes_json)
        except (ValueError, TypeError):
            scopes = provider.scopes_json.split(" ")
    return adapter.build_authorize_url(
        auth_url=provider.auth_url,
        scopes=scopes,
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state_token,
    )


async def exchange_code_for_token(
    provider: OAuthProvider,
    adapter: BaseOAuthAdapter,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Delegate code exchange to the provider adapter."""
    return await adapter.exchange_code(
        token_url=provider.token_url,
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=redirect_uri,
    )


async def save_connection(
    db: AsyncSession,
    provider_code: str,
    workspace_id: Optional[UUID],
    user_id: Optional[UUID],
    token_data: dict,
    adapter: BaseOAuthAdapter,
) -> OAuthConnection:
    """Encrypt tokens and upsert an OAuthConnection row."""
    meta = adapter.normalize_account_metadata(token_data)

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise ValueError("No access_token in provider token response")

    access_token_encrypted = encrypt_string(access_token)
    refresh_token_encrypted = encrypt_string(refresh_token) if refresh_token else None

    expires_at: Optional[datetime] = None
    expires_in = meta.get("expires_in")
    if expires_in:
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        except (ValueError, TypeError):
            pass

    # Upsert: update if same workspace+provider already exists
    existing: Optional[OAuthConnection] = None
    if workspace_id:
        result = await db.execute(
            select(OAuthConnection).where(
                OAuthConnection.workspace_id == workspace_id,
                OAuthConnection.provider_code == provider_code,
            )
        )
        existing = result.scalars().first()
    elif user_id:
        result = await db.execute(
            select(OAuthConnection).where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider_code == provider_code,
            )
        )
        existing = result.scalars().first()

    if existing:
        existing.access_token_encrypted = access_token_encrypted
        existing.refresh_token_encrypted = refresh_token_encrypted
        existing.expires_at = expires_at
        existing.token_type = meta.get("token_type")
        existing.external_account_id = meta.get("external_account_id")
        existing.external_account_name = meta.get("external_account_name")
        existing.status = OAuthConnectionStatus.ACTIVE
        existing.updated_at = datetime.utcnow()
        conn = existing
    else:
        conn = OAuthConnection(
            workspace_id=workspace_id,
            user_id=user_id,
            provider_code=provider_code,
            external_account_id=meta.get("external_account_id"),
            external_account_name=meta.get("external_account_name"),
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            expires_at=expires_at,
            token_type=meta.get("token_type"),
            status=OAuthConnectionStatus.ACTIVE,
        )
        db.add(conn)

    await db.flush()
    return conn


async def refresh_access_token(db: AsyncSession, connection_id: UUID) -> OAuthConnection:
    """Use the stored refresh token to get a new access token."""
    result = await db.execute(
        select(OAuthConnection).where(OAuthConnection.id == connection_id)
    )
    conn = result.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="OAuth connection not found")
    if not conn.refresh_token_encrypted:
        raise HTTPException(status_code=400, detail="No refresh token stored for this connection")

    provider = await get_provider(db, conn.provider_code)
    adapter = get_adapter(conn.provider_code)

    # Get provider credentials from settings
    client_id, client_secret = _get_credentials(conn.provider_code)

    refresh_token = decrypt_string(conn.refresh_token_encrypted)
    token_data = await adapter.refresh_token(
        token_url=provider.token_url,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )

    new_access_token = token_data.get("access_token", "")
    if not new_access_token:
        conn.status = OAuthConnectionStatus.FAILED
        conn.updated_at = datetime.utcnow()
        await db.flush()
        raise ValueError("Provider returned no access_token during refresh")

    conn.access_token_encrypted = encrypt_string(new_access_token)
    if token_data.get("refresh_token"):
        conn.refresh_token_encrypted = encrypt_string(token_data["refresh_token"])

    meta = adapter.normalize_account_metadata(token_data)
    expires_in = meta.get("expires_in")
    if expires_in:
        try:
            conn.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        except (ValueError, TypeError):
            pass

    conn.status = OAuthConnectionStatus.ACTIVE
    conn.updated_at = datetime.utcnow()
    await db.flush()

    await audit_event(
        db,
        action="oauth.token.refreshed",
        entity_type="oauth_connection",
        entity_id=str(conn.id),
        actor_type="service",
        outcome="success",
        workspace_id=conn.workspace_id,
        metadata={"provider_code": conn.provider_code},
    )
    return conn


async def revoke_connection(db: AsyncSession, connection_id: UUID) -> OAuthConnection:
    """Mark a connection as revoked. Does not call provider revoke endpoint (future concern)."""
    result = await db.execute(
        select(OAuthConnection).where(OAuthConnection.id == connection_id)
    )
    conn = result.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="OAuth connection not found")

    conn.status = OAuthConnectionStatus.REVOKED
    conn.updated_at = datetime.utcnow()
    await db.flush()

    await audit_event(
        db,
        action="oauth.connection.revoked",
        entity_type="oauth_connection",
        entity_id=str(conn.id),
        actor_type="user",
        outcome="success",
        workspace_id=conn.workspace_id,
        metadata={"provider_code": conn.provider_code},
    )
    return conn


def _get_credentials(provider_code: str) -> tuple[str, str]:
    """Return (client_id, client_secret) for the given provider from settings."""
    from app.core.config import settings

    mapping = {
        "facebook": (settings.FACEBOOK_CLIENT_ID, settings.FACEBOOK_CLIENT_SECRET),
        "tiktok": (settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET),
        "hubspot": (settings.HUBSPOT_CLIENT_ID, settings.HUBSPOT_CLIENT_SECRET),
        "salesforce": (settings.SALESFORCE_CLIENT_ID, settings.SALESFORCE_CLIENT_SECRET),
    }
    creds = mapping.get(provider_code)
    if not creds or not creds[0] or not creds[1]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth credentials for '{provider_code}' are not configured on this server",
        )
    return creds[0], creds[1]
