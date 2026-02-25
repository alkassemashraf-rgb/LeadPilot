from fastapi import APIRouter
from app.schemas.envelope import ResponseEnvelope, wrap_data

router = APIRouter()

@router.get("/health", response_model=ResponseEnvelope[dict])
async def health_check():
    return wrap_data({"status": "healthy", "version": "1.0.0"})
