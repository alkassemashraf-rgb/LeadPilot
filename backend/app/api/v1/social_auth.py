"""Social login routes — user authentication via Facebook and TikTok.

These routes live under /api/v1/auth/oauth/* and handle USER AUTHENTICATION only.
They are completely separate from /api/v1/oauth/* which manages workspace integrations.

Flow:
  1. GET /auth/oauth/{provider}/start        → returns authorization_url (anonymous)
  2. Provider redirects user to frontend callback with code + state query params
  3. Frontend calls GET /auth/oauth/{provider}/callback?code=...&state=...
  4. Backend resolves/creates user, issues JWT, returns token
"""
import json
import logging
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import security
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    User,
    UserIdentity,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.schemas.social_auth import SocialAuthCallbackResponse, SocialAuthStartResponse
from app.services import oauth_service
from app.services.audit_service import audit_event
from app.services.oauth_providers import get_adapter

logger = logging.getLogger(__name__)

router = APIRouter()

# Only these providers may be used for user authentication.
_ALLOWED_AUTH_PROVIDERS = {"facebook", "tiktok"}


def _get_social_redirect_uri() -> str:
    """Return the frontend social callback URL used as redirect_uri for all social providers."""
    base = (settings.APP_BASE_URL or settings.FRONTEND_URL).rstrip("/")
    return f"{base}/app/auth/social/callback"


@router.get("/{provider_code}/start", response_model=ResponseEnvelope[SocialAuthStartResponse])
async def social_auth_start(
    provider_code: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Begin a social login flow. Returns the provider authorization URL.

    No authentication required — this is the entry point for new and returning users.
    """
    if provider_code not in _ALLOWED_AUTH_PROVIDERS:
        return wrap_error(f"Provider '{provider_code}' is not supported for social login")

    # Check provider credentials configured
    try:
        client_id, client_secret = oauth_service._get_credentials(provider_code)
    except Exception:
        return wrap_error(f"Social login via {provider_code} is not configured on this server")

    # Load provider config (auth_url, scopes, etc.)
    try:
        provider = await oauth_service.get_provider(db, provider_code)
    except Exception as exc:
        return wrap_error(str(exc))

    adapter = get_adapter(provider_code)
    redirect_uri = _get_social_redirect_uri()

    # Create one-time CSRF state, anonymous (no workspace/user yet)
    state = await oauth_service.create_oauth_state(
        db,
        provider_code=provider_code,
        workspace_id=None,
        user_id=None,
        redirect_after=None,
        purpose="social_auth",
    )
    await db.commit()

    authorization_url = oauth_service.build_authorization_url(
        provider=provider,
        adapter=adapter,
        state_token=state.state_token,
        redirect_uri=redirect_uri,
        client_id=client_id,
    )

    await audit_event(
        db,
        action="auth.oauth.start",
        entity_type="oauth_state",
        entity_id=str(state.id),
        actor_type="anonymous",
        outcome="success",
        metadata={"provider_code": provider_code},
    )
    await db.commit()

    logger.info(f"Social auth start: provider={provider_code}")
    return wrap_data(SocialAuthStartResponse(authorization_url=authorization_url))


@router.get("/{provider_code}/callback", response_model=ResponseEnvelope[SocialAuthCallbackResponse])
async def social_auth_callback(
    provider_code: str,
    db: AsyncSession = Depends(get_db),
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
) -> Any:
    """Complete the social login flow. Resolves/creates a user and issues a JWT.

    No authentication required — the browser is redirected here by the provider.
    """
    if provider_code not in _ALLOWED_AUTH_PROVIDERS:
        return wrap_error(f"Provider '{provider_code}' is not supported for social login")

    # Provider-reported error
    if error:
        logger.warning(f"Social auth callback error from provider: provider={provider_code} error={error}")
        await audit_event(
            db, action="auth.oauth.callback.failure", entity_type="oauth_state",
            entity_id="", actor_type="anonymous", outcome="failure",
            metadata={"provider_code": provider_code, "provider_error": error},
        )
        await db.commit()
        return wrap_error(f"Authorization denied by {provider_code}: {error}")

    if not code or not state:
        return wrap_error("Missing code or state parameter")

    # Validate and consume state (one-time use)
    try:
        oauth_state = await oauth_service.validate_and_consume_state(db, state)
    except Exception as exc:
        await audit_event(
            db, action="auth.oauth.callback.failure", entity_type="oauth_state",
            entity_id="", actor_type="anonymous", outcome="failure",
            metadata={"provider_code": provider_code, "reason": "invalid_state"},
        )
        await db.commit()
        return wrap_error(str(exc))

    # Reject if this state was not created for social auth
    if oauth_state.purpose != "social_auth":
        return wrap_error("OAuth state was not issued for social login")

    # Verify provider_code matches state
    if oauth_state.provider_code != provider_code:
        return wrap_error("Provider mismatch in OAuth state")

    # Get credentials and adapter
    try:
        client_id, client_secret = oauth_service._get_credentials(provider_code)
    except Exception:
        return wrap_error(f"Social login via {provider_code} is not configured on this server")

    try:
        provider = await oauth_service.get_provider(db, provider_code)
    except Exception as exc:
        return wrap_error(str(exc))

    adapter = get_adapter(provider_code)
    redirect_uri = _get_social_redirect_uri()

    # Exchange code for access token
    try:
        token_data = await oauth_service.exchange_code_for_token(
            provider=provider,
            adapter=adapter,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as exc:
        logger.error(f"Social auth token exchange failed: provider={provider_code} error={exc}")
        await audit_event(
            db, action="auth.oauth.callback.failure", entity_type="oauth_state",
            entity_id=str(oauth_state.id), actor_type="anonymous", outcome="failure",
            metadata={"provider_code": provider_code, "reason": "token_exchange_failed"},
        )
        await db.commit()
        return wrap_error("Failed to exchange authorization code with provider")

    access_token = token_data.get("access_token", "")
    if not access_token:
        return wrap_error("Provider returned no access token")

    # Fetch user profile from provider
    try:
        profile = await adapter.fetch_user_profile(access_token)
    except Exception as exc:
        logger.error(f"Social auth profile fetch failed: provider={provider_code} error={exc}")
        return wrap_error("Failed to fetch user profile from provider")

    provider_user_id: str = profile.get("provider_user_id", "")
    provider_email: Optional[str] = profile.get("email")
    provider_name: Optional[str] = profile.get("full_name")
    provider_avatar_url: Optional[str] = profile.get("avatar_url")

    if not provider_user_id:
        return wrap_error("Provider did not return a user identifier")

    # --- User resolution logic ---
    new_user = False
    user: Optional[User] = None

    # A) Existing UserIdentity for this (provider_code, provider_user_id)?
    id_result = await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider_code == provider_code,
            UserIdentity.provider_user_id == provider_user_id,
        )
    )
    identity = id_result.scalars().first()

    if identity:
        # Known identity — load the linked user
        user_result = await db.execute(select(User).where(User.id == identity.user_id))
        user = user_result.scalars().first()
        if not user or not user.is_active:
            return wrap_error("Account is inactive")
        logger.info(f"Social auth: existing identity login user_id={user.id} provider={provider_code}")

    else:
        # B) Email match — link to existing account?
        if provider_email:
            email_result = await db.execute(select(User).where(User.email == provider_email))
            user = email_result.scalars().first()

        if user:
            if not user.is_active:
                return wrap_error("Account is inactive")
            # Create identity linked to existing user
            identity = UserIdentity(
                user_id=user.id,
                provider_code=provider_code,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_name=provider_name,
                provider_avatar_url=provider_avatar_url,
            )
            db.add(identity)
            await db.flush()
            logger.info(f"Social auth: linked identity to existing user user_id={user.id} provider={provider_code}")

            await audit_event(
                db, action="auth.oauth.identity.linked", entity_type="user_identity",
                entity_id=str(identity.id), actor_type="user", outcome="success",
                metadata={"provider_code": provider_code, "user_id": str(user.id),
                          "provider_user_id": provider_user_id},
            )

        else:
            # C) Create new user + workspace + identity
            new_user = True

            # TikTok (and any provider) may not provide an email — use placeholder
            email_missing = not provider_email
            email = provider_email or f"{provider_code}_{provider_user_id}@placeholder.local"

            user = User(
                email=email,
                full_name=provider_name,
                hashed_password=None,
                auth_provider=provider_code,
                provider_subject=provider_user_id,
                is_active=True,
                email_verified_at=None if email_missing else __import__("datetime").datetime.utcnow(),
            )
            db.add(user)
            await db.flush()

            workspace = Workspace(name=f"{user.full_name or user.email}'s Workspace")
            db.add(workspace)
            await db.flush()

            membership = WorkspaceMember(
                user_id=user.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OWNER,
            )
            db.add(membership)

            meta_json = json.dumps({"social_email_missing": True}) if email_missing else None
            identity = UserIdentity(
                user_id=user.id,
                provider_code=provider_code,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_name=provider_name,
                provider_avatar_url=provider_avatar_url,
                metadata_json=meta_json,
            )
            db.add(identity)
            await db.flush()

            logger.info(f"Social auth: new user created user_id={user.id} provider={provider_code}")

            await audit_event(
                db, action="auth.oauth.user_created", entity_type="user",
                entity_id=str(user.id), actor_type="system", outcome="success",
                metadata={"provider_code": provider_code, "provider_user_id": provider_user_id,
                          "social_email_missing": email_missing},
            )

    await db.commit()
    await db.refresh(user)

    # Fetch workspace for JWT
    ws_result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).limit(1)
    )
    membership = ws_result.scalars().first()
    workspace_id = membership.workspace_id if membership else None

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = security.create_access_token(
        user.id,
        workspace_id=workspace_id,
        expires_delta=access_token_expires,
    )

    await audit_event(
        db, action="auth.oauth.callback.success", entity_type="user",
        entity_id=str(user.id), actor_type="user", outcome="success",
        metadata={"provider_code": provider_code, "provider_user_id": provider_user_id,
                  "new_user": new_user},
    )
    await db.commit()

    return wrap_data(SocialAuthCallbackResponse(
        access_token=jwt_token,
        token_type="bearer",
        new_user=new_user,
    ))
