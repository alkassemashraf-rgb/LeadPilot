"""
Catalog API — Mission 19
Read-only endpoints for all enumerated reference data.
No authentication required. Safe for 60s client caching.
"""
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.models.models import Plan, PlanEntitlement, SystemModuleConfig
from app.schemas.envelope import wrap_data
from app.core.catalog_registry import (
    INTEGRATION_PROVIDERS,
    AUTOMATION_NODE_TYPES,
    AUTOMATION_TRIGGER_TYPES,
    CONVERSATION_STATUSES,
    MESSAGE_DELIVERY_STATUSES,
    WORKSPACE_ROLES,
    AGENCY_ROLES,
    MODULE_LABELS,
    TIMEZONES,
    LANGUAGES,
    AI_MODELS,
    DEDUPE_STRATEGIES,
    EVENT_SOURCES,
    EVENT_OUTCOMES,
    AUDIT_ACTIONS,
    CONTACT_FIELDS,
)

router = APIRouter()


def _set_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "public, max-age=60"


# ── DB-backed endpoints ──────────────────────────────────────────────


@router.get("/plans")
async def get_plans(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return all active plans with their entitlements."""
    _set_cache(response)
    result = await db.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
    )
    plans = result.scalars().all()

    output = []
    for plan in plans:
        ent_result = await db.execute(
            select(PlanEntitlement).where(PlanEntitlement.plan_id == plan.id)
        )
        entitlements = ent_result.scalars().all()
        output.append(
            {
                "id": str(plan.id),
                "name": plan.name,
                "display_name": plan.display_name,
                "description": plan.description,
                "sort_order": plan.sort_order,
                "entitlements": [
                    {"module_key": e.module_key, "hard_limit": e.hard_limit}
                    for e in entitlements
                ],
            }
        )
    return wrap_data(output)


@router.get("/tiers")
async def get_tiers(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Alias for /catalog/plans — tiers and plans are the same concept."""
    return await get_plans(response, db)


@router.get("/modules")
async def get_modules(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return all system modules with human-readable labels."""
    _set_cache(response)
    result = await db.execute(select(SystemModuleConfig))
    modules = result.scalars().all()
    return wrap_data(
        [
            {
                "key": m.module_name,
                "label": MODULE_LABELS.get(m.module_name, m.module_name),
                "is_enabled": m.is_enabled,
            }
            for m in modules
        ]
    )


# ── Static (registry-backed) endpoints ───────────────────────────────


def _static_endpoint(data: list):
    """Factory for pure-enum catalog endpoints."""

    async def _handler(response: Response) -> Any:
        _set_cache(response)
        return wrap_data(data)

    return _handler


router.add_api_route(
    "/workspace-roles",
    _static_endpoint(WORKSPACE_ROLES),
    methods=["GET"],
)
router.add_api_route(
    "/admin-roles",
    _static_endpoint(AGENCY_ROLES),
    methods=["GET"],
)
router.add_api_route(
    "/integration-providers",
    _static_endpoint(INTEGRATION_PROVIDERS),
    methods=["GET"],
)
router.add_api_route(
    "/automation-node-types",
    _static_endpoint(AUTOMATION_NODE_TYPES),
    methods=["GET"],
)
router.add_api_route(
    "/automation-trigger-types",
    _static_endpoint(AUTOMATION_TRIGGER_TYPES),
    methods=["GET"],
)
router.add_api_route(
    "/conversation-statuses",
    _static_endpoint(CONVERSATION_STATUSES),
    methods=["GET"],
)
router.add_api_route(
    "/message-delivery-statuses",
    _static_endpoint(MESSAGE_DELIVERY_STATUSES),
    methods=["GET"],
)
router.add_api_route(
    "/timezones",
    _static_endpoint(TIMEZONES),
    methods=["GET"],
)
router.add_api_route(
    "/languages",
    _static_endpoint(LANGUAGES),
    methods=["GET"],
)
router.add_api_route(
    "/ai-models",
    _static_endpoint(AI_MODELS),
    methods=["GET"],
)
router.add_api_route(
    "/dedupe-strategies",
    _static_endpoint(DEDUPE_STRATEGIES),
    methods=["GET"],
)
router.add_api_route(
    "/event-sources",
    _static_endpoint(EVENT_SOURCES),
    methods=["GET"],
)
router.add_api_route(
    "/event-outcomes",
    _static_endpoint(EVENT_OUTCOMES),
    methods=["GET"],
)
router.add_api_route(
    "/audit-actions",
    _static_endpoint(AUDIT_ACTIONS),
    methods=["GET"],
)
router.add_api_route(
    "/contact-fields",
    _static_endpoint(CONTACT_FIELDS),
    methods=["GET"],
)
