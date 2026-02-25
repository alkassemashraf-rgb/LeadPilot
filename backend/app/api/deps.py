from typing import List, Optional, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.db import get_db
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == UUID(token_data)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # --- Email Verification Policy Enforcement ---
    # 1. If user is verified, they are good.
    if user.email_verified_at:
        return user
    
    # 2. If user is NOT verified, check if they are past their grace period expiry.
    # Note: SQLite stores naive datetimes. We compare them with datetime.utcnow().
    if user.email_verification_expires_at:
        from datetime import datetime
        now = datetime.utcnow()
        if now > user.email_verification_expires_at:
            # The grace period has expired. Block access.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your 7-day email verification grace period has expired. Please verify your email to continue."
            )
            
    return user

async def get_active_workspace(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_workspace_id: Optional[UUID] = Header(None, alias="X-Workspace-ID")
) -> Workspace:
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID header is required",
        )
    
    # Verify user belongs to workspace and get their role
    result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == x_workspace_id
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this workspace",
        )
    
    result = await db.execute(select(Workspace).where(Workspace.id == x_workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Attach role to the workspace object for convenience in endpoints?
    # Or return a tuple/custom object. For now let's just return the workspace.
    return workspace

def require_role(allowed_roles: List[WorkspaceRole]):
    async def role_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        x_workspace_id: UUID = Header(..., alias="X-Workspace-ID")
    ):
        result = await db.execute(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_id == x_workspace_id
            )
        )
        membership = result.scalars().first()
        if not membership or membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions in this workspace",
            )
        return membership
    return role_checker


def require_email_state(action: str = "verified"):
    """
    Factory dependency enforcing email verification policy per action.

    Policy (Option A — 7-day grace for integrations):
      action="upgrade"               → Must be verified. No grace window.
      action="integrations_connect"  → Allowed if verified OR within 7-day grace.
                                       Blocked after grace window expires with no verification.
      action="verified"              → Alias for upgrade (strict).

    Usage:
        @router.post("/connect")
        async def connect(..., _: User = Depends(require_email_state("integrations_connect"))):
            ...
    """
    from datetime import datetime, timedelta

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        already_verified = current_user.email_verified_at is not None

        if already_verified:
            return current_user   # <<< Always pass if verified

        # --- Unverified path ---
        if action in ("upgrade", "verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Email verification required for this action. "
                    "Please verify your email address first."
                )
            )

        if action == "integrations_connect":
            # Option A: allow within 7-day grace window
            grace_expires = current_user.email_verification_expires_at
            now = datetime.utcnow()

            if grace_expires is not None:
                # Handle both tz-aware and naive datetimes from SQLite
                if hasattr(grace_expires, "tzinfo") and grace_expires.tzinfo:
                    from datetime import timezone
                    now = datetime.now(timezone.utc)

                if now < grace_expires:
                    return current_user  # <<< Within grace — allow

            # Grace expired or never set → block
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Your 7-day email verification grace period has expired. "
                    "Please verify your email address to connect integrations."
                )
            )

        # Unknown action — default to strict
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required."
        )

    return _check


# Convenience alias — strict, no grace
async def require_verified_email(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Guard: blocks if user's email is not verified (no grace window).
    Use for billing / upgrade actions.
    """
    if current_user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Email verification required for this action. "
                "Please verify your email address first."
            )
        )
    return current_user
