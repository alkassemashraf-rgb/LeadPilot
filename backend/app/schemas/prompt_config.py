from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class PromptVersionRead(BaseModel):
    id: UUID
    version_number: int
    business_profile_json: Optional[Dict[str, Any]] = None
    system_prompt_text: str # This becomes the 'compiled' field in UI if needed
    guardrails_json: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    compiled_system_instruction: Optional[str] = None
    temperature: float
    max_tokens_per_execution: int
    created_at: datetime

    class Config:
        from_attributes = True

class PromptConfigRead(BaseModel):
    id: UUID
    name: str
    current_version_id: Optional[UUID]
    versions: List[PromptVersionRead] = []

    class Config:
        from_attributes = True

class PromptVersionCreate(BaseModel):
    structured_data: Dict[str, Any]
    temperature: Optional[float] = 0.7
    max_tokens_per_execution: Optional[int] = 1000
