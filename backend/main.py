from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from app.core.config import settings
from app.core.db import engine
from app.api.v1 import auth, workspaces, health, prompt_config, test_chat, integrations, webhooks, automations, knowledge, analytics
from app.core.seed import seed_modules, seed_admin
from app.api.v1.dispatch import router as dispatch_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.zoho import router as zoho_router
from app.api.v1.admin import router as admin_router
from app.api.v1.admin_auth import router as admin_auth_router
from app.api.v1.diagnostics import router as diagnostics_router
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
    # Seed default module configs
    await seed_modules()
    # Seed initial super admin
    await seed_admin()
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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

# Routers
app.include_router(health.router, prefix=f"{settings.API_V1_STR}", tags=["health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(admin_auth_router, prefix=f"{settings.API_V1_STR}/admin_auth", tags=["admin-auth"])
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

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

@app.get("/")
async def root():
    return {"message": "Welcome to LeadPilot API", "docs": "/docs"}
