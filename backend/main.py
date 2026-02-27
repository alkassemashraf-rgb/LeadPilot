from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from app.core.config import settings
from app.core.db import engine
from app.api.v1 import auth, workspaces, health, prompt_config, test_chat, integrations, webhooks, automations, knowledge, analytics
from app.core.seed import seed_modules, seed_plans, seed_system_settings
from app.api.v1.dispatch import router as dispatch_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.zoho import router as zoho_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_auth import router as admin_auth_router
from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.agency import router as agency_router
from app.api.v1.settings import router as settings_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.support_timeline import router as support_timeline_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.qualification import router as qualification_router
from fastapi import HTTPException
import uuid
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.schemas.envelope import wrap_error

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # Seed default module configs, plans, and system settings
    await seed_modules()
    await seed_plans()
    await seed_system_settings()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Trust proxy headers (essential for HF Spaces to detect HTTPS)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ashrafkassem-leadpilot.hf.space",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "X-Workspace-ID", "Content-Type"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Process time and custom headers
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@app.middleware("http")
async def maintenance_mode_guard(request: Request, call_next):
    """Block non-admin API requests when maintenance_mode is enabled."""
    path = request.url.path
    # Always allow: health, admin, admin_auth, docs, root
    exempt_prefixes = (
        "/health",
        f"{settings.API_V1_STR}/health",
        f"{settings.API_V1_STR}/admin",
        f"{settings.API_V1_STR}/admin_auth",
        f"{settings.API_V1_STR}/catalog",
        "/docs",
        "/openapi.json",
    )
    if path == "/" or any(path.startswith(p) for p in exempt_prefixes):
        return await call_next(request)

    # Only check for API paths
    if path.startswith(settings.API_V1_STR):
        from app.services.settings_service import is_maintenance_mode
        from app.core.db import SessionLocal
        try:
            async with SessionLocal() as db:
                if await is_maintenance_mode(db):
                    return JSONResponse(
                        status_code=503,
                        content=wrap_error("System is in maintenance mode. Please try again later."),
                    )
        except Exception:
            pass  # If settings check fails, don't block requests

    return await call_next(request)

# Routers
app.include_router(health.router, prefix=f"{settings.API_V1_STR}", tags=["health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(admin_auth_router, prefix=f"{settings.API_V1_STR}/admin_auth", tags=["admin-auth"])

logger = logging.getLogger("api")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", "Unknown")
    logger.error(f"[{correlation_id}] HTTP {exc.status_code}: {exc.detail}")
    # Structured dict detail (e.g., from require_module_enabled) — preserve as-is
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "data": None, "error": exc.detail}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=wrap_error(message=str(exc.detail))
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "Unknown")
    logger.error(f"[{correlation_id}] Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=wrap_error(message="Internal Server Error")
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = f"Validation Error: {errors[0]['msg']} at {errors[0]['loc']}" if errors else "Validation Error"
    return JSONResponse(
        status_code=422,
        content=wrap_error(message=msg)
    )
app.include_router(workspaces.router, prefix=f"{settings.API_V1_STR}/workspaces", tags=["workspaces"])
app.include_router(prompt_config.router, prefix=f"{settings.API_V1_STR}/prompt-config", tags=["prompt-config"])
app.include_router(test_chat.router, prefix=f"{settings.API_V1_STR}/test-chat", tags=["test-chat"])
app.include_router(integrations.router, prefix=f"{settings.API_V1_STR}/integrations", tags=["integrations"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["webhooks"])
app.include_router(automations.router, prefix=f"{settings.API_V1_STR}/automations", tags=["automations"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["knowledge"])
app.include_router(dispatch_router, prefix=f"{settings.API_V1_STR}/dispatch", tags=["dispatch"])
app.include_router(inbox_router, prefix=f"{settings.API_V1_STR}/inbox", tags=["inbox"])
app.include_router(zoho_router, prefix=f"{settings.API_V1_STR}", tags=["zoho"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(diagnostics_router, prefix=f"{settings.API_V1_STR}/diagnostics", tags=["diagnostics"])
app.include_router(agency_router, prefix=f"{settings.API_V1_STR}/agency", tags=["agency"])
app.include_router(settings_router, prefix=f"{settings.API_V1_STR}/settings/workspace", tags=["settings"])
app.include_router(audit_logs_router, prefix=f"{settings.API_V1_STR}/audit-logs", tags=["audit-logs"])
app.include_router(support_timeline_router, prefix=f"{settings.API_V1_STR}", tags=["support-timeline"])
app.include_router(catalog_router, prefix=f"{settings.API_V1_STR}/catalog", tags=["catalog"])
app.include_router(qualification_router, prefix=f"{settings.API_V1_STR}/qualification-config", tags=["qualification"])

@app.get("/")
async def root():
    return {"message": "Welcome to LeadPilot API", "docs": "/docs"}
