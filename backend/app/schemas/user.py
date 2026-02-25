from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserRead(UserBase):
    id: UUID
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class MeRead(UserRead):
    """Extended user read with email verification state."""
    email_verified_at: Optional[datetime] = None
    email_verification_expires_at: Optional[datetime] = None
    requires_email_verification: bool = False
    verification_grace_remaining_days: Optional[int] = None


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    workspace_id: Optional[str] = None

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

class GoogleCallback(BaseModel):
    code: str
    state: str
