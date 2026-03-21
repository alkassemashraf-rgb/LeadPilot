"""OAuth Framework schemas — safe, token-free response shapes."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.models.models import OAuthConnectionStatus


class OAuthProviderRead(BaseModel):
    id: UUID
    provider_code: str
    display_name: str
    auth_url: str
    token_url: str
    scopes_json: Optional[str]
    is_active: bool
    supports_refresh_token: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OAuthProviderWithStats(OAuthProviderRead):
    connection_count: int = 0


class OAuthConnectionRead(BaseModel):
    id: UUID
    workspace_id: Optional[UUID]
    user_id: Optional[UUID]
    provider_code: str
    external_account_id: Optional[str]
    external_account_name: Optional[str]
    expires_at: Optional[datetime]
    token_type: Optional[str]
    scopes_json: Optional[str]
    status: OAuthConnectionStatus
    created_at: datetime
    updated_at: datetime
    # NOTE: access_token_encrypted and refresh_token_encrypted are NEVER included here

    model_config = {"from_attributes": True}


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str


class OAuthProviderToggle(BaseModel):
    is_active: bool
