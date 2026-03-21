"""Admin OAuth routes — provider health, connection visibility, provider toggles."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.models import OAuthConnection, OAuthProvider, User
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.schemas.oauth import OAuthConnectionRead, OAuthProviderToggle, OAuthProviderWithStats

router = APIRouter()


async def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Raise 403 if the authenticated user is not a SuperAdmin."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superadmin privileges required")
    return current_user


# ─── List Providers ────────────────────────────────────────────────────────────

@router.get(
    "/providers",
    response_model=ResponseEnvelope[List[OAuthProviderWithStats]],
    summary="List all OAuth providers with connection counts",
)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
):
    result = await db.execute(select(OAuthProvider))
    providers = result.scalars().all()

    # Get connection counts per provider
    count_result = await db.execute(
        select(OAuthConnection.provider_code, func.count(OAuthConnection.id).label("cnt"))
        .group_by(OAuthConnection.provider_code)
    )
    counts = {row.provider_code: row.cnt for row in count_result}

    out = []
    for p in providers:
        data = OAuthProviderWithStats.model_validate(p)
        data.connection_count = counts.get(p.provider_code, 0)
        out.append(data)

    return wrap_data(out)


# ─── List Connections ──────────────────────────────────────────────────────────

@router.get(
    "/connections",
    response_model=ResponseEnvelope[List[OAuthConnectionRead]],
    summary="List all OAuth connections (admin view)",
)
async def list_connections(
    provider_code: Optional[str] = Query(default=None),
    workspace_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
):
    stmt = select(OAuthConnection)
    if provider_code:
        stmt = stmt.where(OAuthConnection.provider_code == provider_code)
    if workspace_id:
        stmt = stmt.where(OAuthConnection.workspace_id == workspace_id)
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    conns = result.scalars().all()
    return wrap_data([OAuthConnectionRead.model_validate(c) for c in conns])


# ─── Toggle Provider ───────────────────────────────────────────────────────────

@router.patch(
    "/providers/{provider_code}",
    response_model=ResponseEnvelope[OAuthProviderWithStats],
    summary="Enable or disable an OAuth provider",
)
async def toggle_provider(
    provider_code: str,
    body: OAuthProviderToggle,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_superadmin),
):
    result = await db.execute(
        select(OAuthProvider).where(OAuthProvider.provider_code == provider_code)
    )
    provider = result.scalars().first()
    if not provider:
        return wrap_error(f"Provider '{provider_code}' not found")

    from datetime import datetime
    provider.is_active = body.is_active
    provider.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(provider)

    count_result = await db.execute(
        select(func.count(OAuthConnection.id)).where(
            OAuthConnection.provider_code == provider_code
        )
    )
    connection_count = count_result.scalar() or 0

    data = OAuthProviderWithStats.model_validate(provider)
    data.connection_count = connection_count
    return wrap_data(data)
