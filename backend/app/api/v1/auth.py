import secrets
import hashlib
import httpx
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from jose import jwt
import redis.asyncio as aioredis

from app.core import security
from app.core.config import settings
from app.core.db import get_db
from app.models.models import User, Workspace, WorkspaceMember, WorkspaceRole, PasswordResetToken, EmailLog, EmailStatus, EmailOutbox, EmailOutboxStatus
from app.schemas.user import Token, UserRead, UserCreate, ForgotPassword, ResetPassword, GoogleCallback, MeRead, ProfileUpdate
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.api.deps import get_current_user
from app.services.audit_service import audit_event

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me", response_model=ResponseEnvelope[MeRead])
async def get_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Return the authenticated user with email verification state."""
    now = datetime.utcnow()
    
    verified = current_user.email_verified_at is not None
    grace_expires = current_user.email_verification_expires_at
    
    # Compute grace remaining days
    grace_remaining_days: Optional[int] = None
    if not verified and grace_expires is not None:
        delta = grace_expires - now
        grace_remaining_days = max(0, delta.days)
    
    requires_verification = not verified
    
    return wrap_data(MeRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        email_verified_at=current_user.email_verified_at,
        email_verification_expires_at=grace_expires,
        requires_email_verification=requires_verification,
        verification_grace_remaining_days=grace_remaining_days,
    ))


@router.patch("/me", response_model=ResponseEnvelope[MeRead])
async def update_profile(
    update_in: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> Any:
    """Update the authenticated user's profile."""
    changed = False

    if update_in.full_name is not None:
        stripped = update_in.full_name.strip()
        if not stripped:
            return wrap_error("Full name cannot be empty")
        current_user.full_name = stripped
        changed = True

    if changed:
        db.add(current_user)
        await audit_event(
            db, action="update_profile", entity_type="user",
            entity_id=str(current_user.id), actor_user_id=current_user.id,
            outcome="success", request=request,
        )
        await db.commit()
        await db.refresh(current_user)

    now = datetime.utcnow()
    verified = current_user.email_verified_at is not None
    grace_expires = current_user.email_verification_expires_at
    grace_remaining_days: Optional[int] = None
    if not verified and grace_expires is not None:
        delta = grace_expires - now
        grace_remaining_days = max(0, delta.days)

    return wrap_data(MeRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        email_verified_at=current_user.email_verified_at,
        email_verification_expires_at=grace_expires,
        requires_email_verification=not verified,
        verification_grace_remaining_days=grace_remaining_days,
    ))


@router.post("/login", response_model=ResponseEnvelope[Token])
async def login(
    request: Request, db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        await audit_event(
            db, action="user_login", entity_type="user",
            entity_id=str(user.id) if user else form_data.username,
            actor_user_id=user.id if user else None,
            outcome="failure", error_code="invalid_credentials", request=request,
        )
        await db.commit()
        return wrap_error("Incorrect email or password")

    if not user.is_active:
        await audit_event(
            db, action="user_login", entity_type="user",
            entity_id=str(user.id), actor_user_id=user.id,
            outcome="failure", error_code="inactive_user", request=request,
        )
        await db.commit()
        return wrap_error("Inactive user")
    
    # Get the first workspace the user belongs to for the token (default context)
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).limit(1)
    )
    membership = result.scalars().first()
    workspace_id = membership.workspace_id if membership else None
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "access_token": security.create_access_token(
            user.id, workspace_id=workspace_id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
    await audit_event(
        db, action="user_login", entity_type="user",
        entity_id=str(user.id), actor_user_id=user.id,
        outcome="success", request=request,
    )
    await db.commit()
    return wrap_data(token_data)

@router.post("/signup", response_model=ResponseEnvelope[UserRead])
async def signup(
    *, db: AsyncSession = Depends(get_db), user_in: UserCreate, request: Request
) -> Any:
    """Create new user and a default workspace."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        return wrap_error("A user with this email already exists.")
    
    now_naive = datetime.utcnow()

    # Create User
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        email_verification_expires_at=now_naive + timedelta(days=settings.EMAIL_VERIFICATION_GRACE_DAYS),
        email_verification_sent_at=now_naive,
    )
    db.add(db_user)
    await db.flush() # Get ID before commit
    
    # Create Default Workspace
    db_workspace = Workspace(name=f"{db_user.full_name or db_user.email}'s Workspace")
    db.add(db_workspace)
    await db.flush()
    
    # Create Membership
    db_membership = WorkspaceMember(
        user_id=db_user.id,
        workspace_id=db_workspace.id,
        role=WorkspaceRole.OWNER
    )
    db.add(db_membership)
    
    # Generate email verification token
    from app.models.models import EmailVerificationToken
    verify_token = secrets.token_urlsafe(32)
    verify_token_hash = hashlib.sha256(verify_token.encode()).hexdigest()
    
    db_verify_token = EmailVerificationToken(
        user_id=db_user.id,
        token_hash=verify_token_hash,
        expires_at=now_naive + timedelta(days=settings.EMAIL_VERIFICATION_GRACE_DAYS),
    )
    db.add(db_verify_token)
    
    # Create EmailLog
    email_log = EmailLog(
        user_id=db_user.id,
        email_type="verify_email",
        recipient=db_user.email,
        subject=f"Verify your email for {settings.PROJECT_NAME}",
        status=EmailStatus.PENDING,
        attempt_count=0
    )
    db.add(email_log)
    await db.flush()
    
    # Create EmailOutbox
    outbox = EmailOutbox(
        email_log_id=email_log.id,
        email_type="verify_email",
        payload_json={"to_email": db_user.email, "token": verify_token},
        status=EmailOutboxStatus.PENDING
    )
    db.add(outbox)

    await audit_event(
        db, action="user_signup", entity_type="user",
        entity_id=str(db_user.id), actor_user_id=db_user.id,
        outcome="success", request=request,
    )
    await db.commit()
    await db.refresh(db_user)

    # Attempt fast-path send
    try:
        from app.workers.email_tasks import send_email_task_v2
        send_email_task_v2.delay(str(outbox.id))
    except Exception as e:
        logger.warning(f"Worker broker unavailable: {e}")
    
    return wrap_data(db_user)

@router.get("/verify-email", response_model=ResponseEnvelope[dict])
async def verify_email(
    token: str, request: Request, db: AsyncSession = Depends(get_db)
) -> Any:
    """Verify user email from token delivered by email."""
    from app.models.models import EmailVerificationToken
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),
        )
    )
    db_token = result.scalars().first()
    
    if not db_token:
        await audit_event(
            db, action="verify_email", entity_type="email_token",
            entity_id="unknown", outcome="failure",
            error_code="invalid_token", request=request,
        )
        await db.commit()
        return wrap_error("Invalid or already-used verification link.")
    
    # Check expiry - use naive comparison since SQLite stores naive datetimes
    token_expires = db_token.expires_at
    now_naive = datetime.utcnow()
    if hasattr(token_expires, 'tzinfo') and token_expires.tzinfo:
        now_check = now
    else:
        now_check = now_naive
    
    if token_expires < now_check:
        await audit_event(
            db, action="verify_email", entity_type="email_token",
            entity_id=str(db_token.user_id), actor_user_id=db_token.user_id,
            outcome="failure", error_code="token_expired", request=request,
        )
        await db.commit()
        return wrap_error("This verification link has expired. Please request a new one.")
    
    # Mark token used and verify user
    db_token.used_at = now_naive
    
    user = await db.get(User, db_token.user_id)
    if not user:
        return wrap_error("User not found.")
    
    user.email_verified_at = now_naive

    await audit_event(
        db, action="verify_email", entity_type="user",
        entity_id=str(user.id), actor_user_id=user.id,
        outcome="success", request=request,
    )
    await db.commit()
    return wrap_data({"message": "Email verified successfully! You can now use all LeadPilot features."})

@router.post("/resend-verification", response_model=ResponseEnvelope[dict])
async def resend_verification(
    *, db: AsyncSession = Depends(get_db), body: dict, request: Request
) -> Any:
    """Resend a verification email. Rate limit: 5 per hour per email."""
    from app.models.models import EmailVerificationToken
    
    email = body.get("email", "").strip().lower()
    if not email:
        return wrap_error("Email is required.")
    
    success_msg = {"message": "If the email exists and is unverified, a new verification link has been sent."}
    
    # Rate Limit via Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        rl_key = f"rate_limit:resend_verification:{email}"
        attempts = await redis_client.incr(rl_key)
        if attempts == 1:
            await redis_client.expire(rl_key, 3600)
        await redis_client.aclose()
        
        if attempts > 5:
            return wrap_error("Too many verification emails sent. Please wait an hour before trying again.")
    except Exception:
        pass
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user or user.email_verified_at is not None:
        return wrap_data(success_msg)
    
    now_naive = datetime.utcnow()

    # Generate new token
    verify_token = secrets.token_urlsafe(32)
    verify_token_hash = hashlib.sha256(verify_token.encode()).hexdigest()
    
    db_token = EmailVerificationToken(
        user_id=user.id,
        token_hash=verify_token_hash,
        expires_at=now_naive + timedelta(days=settings.EMAIL_VERIFICATION_GRACE_DAYS),
    )
    db.add(db_token)
    
    # Update user expiry stamp
    user.email_verification_expires_at = now_naive + timedelta(days=settings.EMAIL_VERIFICATION_GRACE_DAYS)
    user.email_verification_sent_at = now_naive
    
    # Create EmailLog + Outbox
    email_log = EmailLog(
        user_id=user.id,
        email_type="verify_email",
        recipient=user.email,
        subject=f"Verify your email for {settings.PROJECT_NAME}",
        status=EmailStatus.PENDING,
        attempt_count=0
    )
    db.add(email_log)
    await db.flush()
    
    outbox = EmailOutbox(
        email_log_id=email_log.id,
        email_type="verify_email",
        payload_json={"to_email": user.email, "token": verify_token},
        status=EmailOutboxStatus.PENDING
    )
    db.add(outbox)
    await audit_event(
        db, action="resend_verification", entity_type="user",
        entity_id=str(user.id), actor_user_id=user.id,
        outcome="success", request=request,
    )
    await db.commit()

    try:
        from app.workers.email_tasks import send_email_task_v2
        send_email_task_v2.delay(str(outbox.id))
    except Exception as e:
        logger.warning(f"Worker broker unavailable: {e}")

    return wrap_data(success_msg)


@router.post("/forgot-password", response_model=ResponseEnvelope[dict])
async def forgot_password(
    *, db: AsyncSession = Depends(get_db), forgot_in: ForgotPassword, request: Request
) -> Any:
    """Request a password reset."""
    
    # Security: Always return success to avoid user enumeration
    success_msg = {"message": "If the email exists, you will receive a reset link shortly."}

    # Rate Limiting: Max 5 per hour per user string
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        rl_key = f"rate_limit:forgot_password:{forgot_in.email}"
        
        attempts = await redis_client.incr(rl_key)
        if attempts == 1:
            await redis_client.expire(rl_key, 3600)
            
        if attempts > 5:
            return wrap_error("Rate limit exceeded for password resets")
    except Exception:
        # If redis fails, do we bypass rate limiting? Yes, degrades gracefully.
        pass
    finally:
        try:
            await redis_client.aclose()
        except Exception:
            pass

    result = await db.execute(select(User).where(User.email == forgot_in.email))
    user = result.scalars().first()
    
    if user:
        # Generate token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Save to DB
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(reset_token)
        
        # Create EmailLog
        email_log = EmailLog(
            user_id=user.id,
            email_type="password_reset",
            recipient=user.email,
            subject="Reset your LeadPilot password",
            status=EmailStatus.PENDING,
            attempt_count=0
        )
        db.add(email_log)
        await db.flush() # Need `email_log.id` for Outbox
        
        # Create EmailOutbox ensuring atomic lock
        outbox = EmailOutbox(
            email_log_id=email_log.id,
            email_type="password_reset",
            payload_json={"to_email": user.email, "token": token, "email_log_id": str(email_log.id)},
            status=EmailOutboxStatus.PENDING
        )
        db.add(outbox)
        
        await db.commit()
        await db.refresh(outbox)
        
        # Attempt fast-path execution (optional but responsive)
        try:
            from app.workers.email_tasks import send_email_task_v2
            send_email_task_v2.delay(str(outbox.id))
        except Exception as e:
            logger.warning(f"Worker broker unavailable for fast-path enqueue: {e}")

    await audit_event(
        db, action="forgot_password", entity_type="user",
        entity_id=forgot_in.email, outcome="success", request=request,
    )
    await db.commit()
    return wrap_data(success_msg)

@router.post("/reset-password", response_model=ResponseEnvelope[dict])
async def reset_password(
    *, db: AsyncSession = Depends(get_db), reset_in: ResetPassword
) -> Any:
    """Reset password using token."""
    token_hash = hashlib.sha256(reset_in.token.encode()).hexdigest()
    
    # Find valid token
    result = await db.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
            PasswordResetToken.used_at.is_(None)
        )
    )
    reset_token = result.scalars().first()
    
    if not reset_token:
        return wrap_error("Invalid or expired reset token")
    
    # Find user
    user = await db.get(User, reset_token.user_id)
    if not user:
        return wrap_error("User not found")
    
    # Update password
    user.hashed_password = security.get_password_hash(reset_in.new_password)
    reset_token.used_at = datetime.now(timezone.utc)
    
    db.add(user)

    db.add(reset_token)
    await db.commit()
    
    return wrap_data({"message": "Password updated successfully"})

def get_google_redirect_uri() -> str:
    """Helper to get the correct Google redirect URI for production (Hugging Face) and local environments."""
    if settings.GOOGLE_OAUTH_REDIRECT_URI:
        return settings.GOOGLE_OAUTH_REDIRECT_URI

    # Use the frontend base URL so the redirect_uri matches the frontend callback page,
    # not the backend server (which runs on a different port in local dev).
    base = (settings.APP_BASE_URL or settings.FRONTEND_URL).rstrip("/")
    redirect_uri = f"{base}/auth/google/callback"
    logger.info(f"Google OAuth: Generated redirect_uri={redirect_uri}")
    return redirect_uri

@router.get("/google/start", response_model=ResponseEnvelope[dict])
async def google_auth_start() -> Any:
    """Generate Google auth URL."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        return wrap_error("Google OAuth credentials not configured on backend.")

    state = security.create_access_token("google_state", expires_delta=timedelta(minutes=10))
    
    redirect_uri = get_google_redirect_uri()
    logger.info(f"Google OAuth START: Starting flow with redirect_uri={redirect_uri}")

    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }
    # Properly construct URL with params
    from urllib.parse import urlencode
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return wrap_data({"auth_url": auth_url})

@router.post("/google/callback", response_model=ResponseEnvelope[Token])
async def google_auth_callback(
    *, db: AsyncSession = Depends(get_db), callback_data: GoogleCallback
) -> Any:
    """Handle Google OAuth callback."""
    # 1. Validate state
    try:
        payload = jwt.decode(callback_data.state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("sub") != "google_state":
            return wrap_error("Invalid state")
    except Exception:
        return wrap_error("Invalid or expired state")

    # 2. Exchange code for token
    redirect_uri = get_google_redirect_uri()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "code": callback_data.code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        if token_response.status_code != 200:
            return wrap_error(f"Failed to exchange code: {token_response.text}")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # 3. Get user info
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_info_response.status_code != 200:
            return wrap_error("Failed to fetch user info")
        
        user_info = user_info_response.json()
        email = user_info.get("email")
        google_id = user_info.get("sub")
        full_name = user_info.get("name")
        email_verified = user_info.get("email_verified", False)

        if not email or not email_verified:
            return wrap_error("Email not verified by Google")

        # Check allowed domains
        if settings.GOOGLE_OAUTH_ALLOWED_DOMAINS:
            domain = email.split("@")[-1]
            if domain not in settings.GOOGLE_OAUTH_ALLOWED_DOMAINS:
                return wrap_error("Domain not allowed")

        # 4. Handle user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                full_name=full_name,
                auth_provider="google",
                provider_subject=google_id,
                is_active=True,
                email_verified_at=datetime.utcnow(),
            )
            db.add(user)
            await db.flush()
            
            # Create Default Workspace
            db_workspace = Workspace(name=f"{user.full_name or user.email}'s Workspace")
            db.add(db_workspace)
            await db.flush()
            
            # Create Membership
            db_membership = WorkspaceMember(
                user_id=user.id,
                workspace_id=db_workspace.id,
                role=WorkspaceRole.OWNER
            )
            db.add(db_membership)
            await db.commit()
            await db.refresh(user)
        else:
            # Update user info if needed
            user.auth_provider = "google"
            user.provider_subject = google_id
            if full_name:
                user.full_name = full_name
            # Google confirmed email — mark verified if not already
            if user.email_verified_at is None:
                user.email_verified_at = datetime.utcnow()
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # 5. Issue JWT
        result = await db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user.id).limit(1)
        )
        membership = result.scalars().first()
        workspace_id = membership.workspace_id if membership else None
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "access_token": security.create_access_token(
                user.id, workspace_id=workspace_id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
        }
        return wrap_data(token_data)
