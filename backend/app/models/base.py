from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field

class BaseIDModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceScopedModel(BaseIDModel):
    workspace_id: UUID = Field(index=True, foreign_key="workspace.id")
