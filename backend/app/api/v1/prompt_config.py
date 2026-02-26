from typing import List, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, PromptConfig, PromptVersion
from app.schemas.prompt_config import PromptConfigRead, PromptVersionRead, PromptVersionCreate
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.config import settings
from app.core.modules import require_module_enabled, MODULE_PROMPT_STUDIO
from app.services.entitlements import require_entitlement

router = APIRouter()

def compile_prompt(data: Dict[str, Any]) -> str:
    """Compile structured form data into a single system instruction block."""
    basics = data.get("basics", {})
    behavior = data.get("behavior", {})
    qualification = data.get("qualification", {})
    escalation = data.get("escalation", {})
    pricing = data.get("pricing", {})
    
    lines = []
    lines.append(f"Business: {basics.get('business_name', 'LeadPilot Client')}")
    lines.append(f"Industry: {basics.get('industry', 'General Service')}")
    if basics.get("services"):
        lines.append(f"Services: {', '.join(basics.get('services', []))}")
    
    lines.append(f"\nRole: {behavior.get('assistant_role', 'Helpful assistant')}")
    lines.append(f"Tone: {behavior.get('tone', 'Professional')}")
    if behavior.get("primary_goal"):
        lines.append(f"Primary Goal: {behavior.get('primary_goal')}")
    if behavior.get("always_do"):
        lines.append(f"ALWAYS DO: {behavior.get('always_do')}")
    if behavior.get("never_do"):
        lines.append(f"NEVER DO: {behavior.get('never_do')}")
        
    details = qualification.get("required_details", [])
    if details:
        lines.append(f"\nLead Qualification: Collect {', '.join(details)}. Ask max {qualification.get('max_questions_at_once', 1)} question(s) at a time.")
    
    if escalation.get("escalate_on_human_request"):
        lines.append(f"\nEscalation: {escalation.get('escalation_message', 'Handing you over to a human team member.')}")
        
    if pricing.get("never_invent_pricing"):
        policy = pricing.get("pricing_policy_text", "Refer to our official documentation for pricing.")
        lines.append(f"\nPricing Guardrail: Never invent pricing. {policy}")
        
    return "\n".join(lines)

@router.get("", response_model=ResponseEnvelope[PromptConfigRead], dependencies=[Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "read")), Depends(require_entitlement("prompt_studio"))])
async def get_prompt_config(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Get the current prompt config and the last 10 versions."""
    result = await db.execute(
        select(PromptConfig).where(PromptConfig.workspace_id == workspace.id)
    )
    config = result.scalars().first()
    
    if not config:
        config = PromptConfig(workspace_id=workspace.id, name="Default Config")
        db.add(config)
        await db.commit()
        await db.refresh(config)

    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.prompt_config_id == config.id)
        .order_by(desc(PromptVersion.version_number))
        .limit(10)
    )
    versions = result.scalars().all()
    
    config_read = PromptConfigRead(
        id=config.id,
        name=config.name,
        current_version_id=config.current_version_id,
        versions=[PromptVersionRead.model_validate(v) for v in versions]
    )
    
    return wrap_data(config_read)

import logging
logger = logging.getLogger(__name__)

@router.post("", response_model=ResponseEnvelope[PromptVersionRead], dependencies=[Depends(require_module_enabled(MODULE_PROMPT_STUDIO, "write")), Depends(require_entitlement("prompt_studio", increment=True))])
async def create_prompt_version(
    *,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    version_in: PromptVersionCreate
) -> Any:
    """Create a new version of the prompt config using structured form data."""
    logger.info(f"Saving new prompt version for workspace: {workspace.id}")
    
    result = await db.execute(
        select(PromptConfig).where(PromptConfig.workspace_id == workspace.id)
    )
    config = result.scalars().first()
    
    if not config:
        logger.info(f"Creating missing PromptConfig for workspace: {workspace.id}")
        config = PromptConfig(workspace_id=workspace.id, name="Default Config")
        db.add(config)
        await db.flush()

    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.prompt_config_id == config.id)
        .order_by(desc(PromptVersion.version_number))
        .limit(1)
    )
    latest = result.scalars().first()
    next_version = (latest.version_number + 1) if latest else 1
    logger.info(f"New prompt version number will be: {next_version}")

    # Compile instruction from structured data
    compiled_text = compile_prompt(version_in.structured_data)

    new_version = PromptVersion(
        prompt_config_id=config.id,
        version_number=next_version,
        structured_data=version_in.structured_data,
        compiled_system_instruction=compiled_text,
        system_prompt_text=compiled_text, # Sync for legacy compatibility
        model=settings.GEMINI_MODEL,
        temperature=version_in.temperature if version_in.temperature is not None else 0.7,
        max_tokens_per_execution=version_in.max_tokens_per_execution or 1000
    )
    db.add(new_version)
    await db.flush()
    
    logger.info(f"Updating current_version_id for config: {config.id} to new version: {new_version.id}")
    config.current_version_id = new_version.id
    db.add(config)
    
    try:
        await db.commit()
        logger.info(f"Successfully saved prompt version {next_version} for workspace {workspace.id}")
    except Exception as e:
        logger.error(f"FAILED to save prompt version: {str(e)}", exc_info=True)
        await db.rollback()
        return wrap_error(f"Database error while saving prompt: {str(e)}")
        
    await db.refresh(new_version)
    return wrap_data(new_version)
