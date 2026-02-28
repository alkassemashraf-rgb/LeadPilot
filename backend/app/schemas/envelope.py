from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None

def wrap_data(data: Any) -> dict:
    return {"success": True, "data": data, "error": None}

def wrap_error(message: str) -> dict:
    return {"success": False, "data": None, "error": message}
