from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import security
from app.core.config import settings
from app.core.db import get_db
from app.models.models import User
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.api.deps import get_current_user

router = APIRouter()


class AdminLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=ResponseEnvelope[dict])
async def admin_login(
    body: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Admin login — JSON body {email, password}. Returns JWT if user is superadmin."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalars().first()

    if not user or not user.hashed_password:
        return wrap_error("Invalid email or password")

    if not security.verify_password(body.password, user.hashed_password):
        return wrap_error("Invalid email or password")

    if not user.is_active:
        return wrap_error("Account is disabled")

    if not user.is_superuser:
        return wrap_error("Admin privileges required")

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return wrap_data({"access_token": access_token, "token_type": "bearer"})


@router.get("/me", response_model=ResponseEnvelope[dict])
async def admin_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return the authenticated admin user info."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return wrap_data({
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_superuser": current_user.is_superuser,
    })
