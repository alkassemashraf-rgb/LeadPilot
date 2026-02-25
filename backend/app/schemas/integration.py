from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.models import IntegrationStatus

class IntegrationRead(BaseModel):
    id: UUID
    provider: str
    status: IntegrationStatus
    connected_at: Optional[datetime]
    last_checked_at: Optional[datetime]
    last_error: Optional[str]
    provider_workspace_id: Optional[str]

    class Config:
        from_attributes = True

class IntegrationConnect(BaseModel):
    # Flexible container for provider-specific credentials
    config: Dict[str, Any]
    provider_workspace_id: Optional[str] = None
