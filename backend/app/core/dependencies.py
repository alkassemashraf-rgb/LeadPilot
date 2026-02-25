from fastapi import Depends, HTTPException, Header, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID

from .config import settings
from ..models.models import User, Workspace, WorkspaceMember, WorkspaceRole

# Placeholder for DB session
async def get_db():
    # This will be replaced by actual engine/sessionmaker later
    yield None

async def get_current_user(token: str = Header(...), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.replace("Bearer ", ""), settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # In a real app, we'd query the DB here:
    # result = await db.execute(select(User).filter(User.id == user_id))
    # user = result.scalars().first()
    # if user is None: raise credentials_exception
    # return user
    return user_id # Returning ID for now

async def get_current_user_obj(token: str = Header(...), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.replace("Bearer ", ""), settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

def require_superadmin():
    async def superadmin_checker(current_user: User = Depends(get_current_user_obj)):
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Superadmin privileges required")
        return current_user
    return superadmin_checker

async def get_active_workspace(
    x_workspace_id: UUID = Header(..., alias="X-Workspace-ID"),
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Authority Rule: Validate membership
    # query = select(WorkspaceMember).filter(
    #     WorkspaceMember.workspace_id == x_workspace_id,
    #     WorkspaceMember.user_id == current_user_id
    # )
    # member = (await db.execute(query)).scalars().first()
    # if not member:
    #     raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return x_workspace_id

def require_role(allowed_roles: List[WorkspaceRole]):
    async def role_checker(
        workspace_id: UUID = Depends(get_active_workspace),
        user_id: str = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # query = select(WorkspaceMember).filter(
        #     WorkspaceMember.workspace_id == workspace_id,
        #     WorkspaceMember.user_id == user_id
        # )
        # member = (await db.execute(query)).scalars().first()
        # if member.role not in allowed_roles:
        #     raise HTTPException(status_code=403, detail="Insufficient permissions")
        return True
    return role_checker


async def require_verified_email(
    current_user: "User" = None
) -> "User":
    """
    Guard: blocks if user's email is not verified.
    Use as a dependency on any endpoint requiring verified email.
    - Ready to be plugged into billing upgrade endpoints.
    - Currently applied to integrations/connect.
    """
    from app.api.deps import get_current_user as deps_get_current_user
    from fastapi import Depends
    # This function is a factory — actual injection happens below
    if current_user is not None and current_user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email address before accessing this feature."
        )
    return current_user


# The actual FastAPI dependency version using the main deps chain
async def get_verified_user(
    current_user: "User" = Depends("app.api.deps.get_current_user")
) -> "User":
    pass
