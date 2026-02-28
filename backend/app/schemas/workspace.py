from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.models.models import WorkspaceRole

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceRead(WorkspaceBase):
    id: UUID
    subscription_tier: str

    class Config:
        from_attributes = True

class MemberRead(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str] = None
    role: WorkspaceRole

    class Config:
        from_attributes = True

class MemberInvite(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER

class MemberUpdateRole(BaseModel):
    role: WorkspaceRole
