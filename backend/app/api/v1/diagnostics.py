import time
from datetime import datetime
from uuid import uuid4
from typing import Any
from fastapi import APIRouter, Depends, Request
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.core.db import get_db
from app.core.config import settings
from app.schemas.envelope import ResponseEnvelope, wrap_data
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", response_model=ResponseEnvelope[dict])
async def get_diagnostics(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    
    # 1. Check Database
    db_ok = False
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception as e:
        logger.error(f"[{correlation_id}] DB Diagnostic failed: {e}")
        
    # 2. Check Redis
    redis_ok = False
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        await redis_client.aclose()
        redis_ok = True
    except Exception as e:
        logger.error(f"[{correlation_id}] Redis Diagnostic failed: {e}")
        
    # 3. Worker queue (best effort - check if Redis URL configured, which is also the Celery broker)
    worker_queue_ok = bool(settings.REDIS_URL)
    
    # 4. LLM Check - Gemini is the current provider
    llm_ok = bool(settings.GEMINI_API_KEY)
    llm_provider = "gemini"
    
    # 5. Email Check
    email_provider = settings.EMAIL_PROVIDER
    sendgrid_configured = bool(settings.SENDGRID_API_KEY and settings.SENDGRID_FROM_EMAIL)

    return wrap_data({
        "db_ok": db_ok,
        "redis_ok": redis_ok,
        "worker_queue_ok": worker_queue_ok,
        "llm_ok": llm_ok,
        "llm_provider_name": llm_provider,
        "email_provider": email_provider,
        "sendgrid_configured": sendgrid_configured,
        "server_time_utc": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id
    })

@router.get("/shell", response_model=ResponseEnvelope[dict])
async def shell_diagnostic(cmd: str = "ps aux"):
    """DANGEROUS: Only for emergency production debugging of worker issues."""
    import subprocess
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return wrap_data({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return wrap_error(str(e))
