"""
Prompt Compiler Service — Mission 20 + Mission 29 enhancements
Single source of truth for workspace AI context compilation.
Used by Test Chat AND Runtime AI_REPLY.
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    PromptConfig,
    PromptVersion,
    WorkspaceKnowledgeFile,
    QualificationConfig,
    QualificationCriterion,
)

logger = logging.getLogger(__name__)

# Stable section separators (never change — part of the prompt contract)
SEP_BUSINESS_PROFILE = "=== BUSINESS PROFILE ==="
SEP_GUARDRAILS = "=== GUARDRAILS ==="
SEP_KNOWLEDGE_BASE = "=== KNOWLEDGE BASE (FILES) ==="
SEP_QUALIFICATION = "=== LEAD QUALIFICATION ==="
SEP_QUALIFICATION_CRITERIA = "=== QUALIFICATION CRITERIA ==="
SEP_STEP_GOAL = "=== STEP GOAL ==="
SEP_TASKS = "=== TASKS ==="
SEP_STEP_INSTRUCTIONS = "=== STEP INSTRUCTIONS ==="
SEP_EXPECTED_OUTPUTS = "=== EXPECTED OUTPUTS ==="

# Max chars per knowledge file excerpt
MAX_CHARS_PER_FILE = 4000


@dataclass
class CompiledPrompt:
    """Immutable result of a compilation pass."""
    system_instruction: str
    temperature: float
    max_tokens: int
    version_id: Optional[UUID] = None
    version_number: Optional[int] = None
    knowledge_file_count: int = 0
    qualification_question_count: int = 0


async def compile_workspace_prompt(
    workspace_id: UUID,
    db: AsyncSession,
    *,
    include_files: bool = True,
    include_qualification: bool = True,
    step_config: Optional[Dict[str, Any]] = None,
    query_hint: Optional[str] = None,
) -> CompiledPrompt:
    """
    Assemble the full system instruction for a workspace.

    Parameters
    ----------
    workspace_id : UUID
        The workspace to compile for.
    db : AsyncSession
        Active database session.
    include_files : bool
        Whether to include knowledge file text. Default True.
    include_qualification : bool
        Whether to include qualification config section. Default True.
    step_config : Optional[Dict]
        If provided, appends step-level goal/tasks/extra_instructions
        (used by runtime AI_REPLY for automation steps).
    query_hint : Optional[str]
        If provided, uses keyword-based chunk retrieval instead of full
        file text. Pass the last user message for relevance matching.

    Returns
    -------
    CompiledPrompt
        Dataclass with system_instruction, temperature, max_tokens, metadata.
    """
    # 1. Fetch active PromptVersion
    config_result = await db.execute(
        select(PromptConfig).where(PromptConfig.workspace_id == workspace_id)
    )
    config = config_result.scalars().first()
    if not config or not config.current_version_id:
        return CompiledPrompt(
            system_instruction="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=1000,
        )

    version = await db.get(PromptVersion, config.current_version_id)
    if not version:
        return CompiledPrompt(
            system_instruction="You are a helpful assistant.",
            temperature=0.7,
            max_tokens=1000,
        )

    # 2. Build sections
    sections: List[str] = []

    # Core compiled instruction (from structured form data)
    if version.system_prompt_text:
        sections.append(version.system_prompt_text)

    # Business profile
    if version.business_profile_json:
        sections.append(f"\n{SEP_BUSINESS_PROFILE}")
        sections.append(json.dumps(version.business_profile_json, indent=2))

    # Guardrails
    if version.guardrails_json:
        sections.append(f"\n{SEP_GUARDRAILS}")
        sections.append(json.dumps(version.guardrails_json, indent=2))

    # 3. Knowledge files / chunks
    kb_count = 0
    if include_files:
        if query_hint:
            # Mission 29: Use chunk-based retrieval for smarter context
            from app.services.knowledge_chunker import retrieve_relevant_chunks
            chunk_texts = await retrieve_relevant_chunks(
                db, workspace_id, query_hint, max_chunks=8,
            )
            if chunk_texts:
                sections.append(f"\n{SEP_KNOWLEDGE_BASE}")
                for ct in chunk_texts:
                    sections.append(ct)
                kb_count = len(chunk_texts)
        else:
            # Backward compat: include full file excerpts
            files_result = await db.execute(
                select(WorkspaceKnowledgeFile).where(
                    WorkspaceKnowledgeFile.workspace_id == workspace_id,
                    WorkspaceKnowledgeFile.extracted_text.isnot(None),
                    WorkspaceKnowledgeFile.status == "READY",
                )
            )
            files = files_result.scalars().all()
            if files:
                sections.append(f"\n{SEP_KNOWLEDGE_BASE}")
                for f in files:
                    text = f.extracted_text
                    if len(text) > MAX_CHARS_PER_FILE:
                        text = text[:MAX_CHARS_PER_FILE] + "\n[... truncated]"
                    sections.append(f"--- {f.filename} ---")
                    sections.append(text)
                kb_count = len(files)

    # 4. Qualification config (questions to collect)
    qual_count = 0
    if include_qualification:
        qual_result = await db.execute(
            select(QualificationConfig).where(
                QualificationConfig.workspace_id == workspace_id
            )
        )
        qual = qual_result.scalars().first()
        if qual and qual.qualification_questions:
            enabled_questions = [
                q for q in qual.qualification_questions if q.get("enabled", True)
            ]
            if enabled_questions:
                sections.append(f"\n{SEP_QUALIFICATION}")
                sections.append(
                    "You must collect the following information from the lead:"
                )
                for q in sorted(enabled_questions, key=lambda x: x.get("order", 0)):
                    sections.append(f"- {q['label']}")
                qual_count = len(enabled_questions)

    # 4b. Qualification criteria (evaluation rules — Mission 29)
    if include_qualification:
        criteria_result = await db.execute(
            select(QualificationCriterion).where(
                QualificationCriterion.workspace_id == workspace_id,
                QualificationCriterion.is_enabled.is_(True),
            ).order_by(QualificationCriterion.sort_order)
        )
        criteria = criteria_result.scalars().all()
        if criteria:
            sections.append(f"\n{SEP_QUALIFICATION_CRITERIA}")
            sections.append("Evaluate each lead against these criteria:")
            for c in criteria:
                line = f"- {c.label}"
                if c.description:
                    line += f": {c.description}"
                line += f" [type: {c.criterion_type}]"
                if c.criterion_type == "enum" and c.enum_values:
                    line += f" (options: {', '.join(c.enum_values)})"
                sections.append(line)

    # 5. Step-level overrides (for automation AI_REPLY nodes)
    if step_config:
        goal = step_config.get("goal")
        tasks = step_config.get("tasks", [])
        extra = step_config.get("extra_instructions")

        if goal:
            sections.append(f"\n{SEP_STEP_GOAL}")
            sections.append(goal)

        if tasks and any(t.strip() for t in tasks if isinstance(t, str)):
            sections.append(f"\n{SEP_TASKS}")
            for t in tasks:
                if isinstance(t, str) and t.strip():
                    sections.append(f"- {t.strip()}")

        if extra:
            sections.append(f"\n{SEP_STEP_INSTRUCTIONS}")
            sections.append(extra)

        # Mission 29: Output schema
        output_schema = step_config.get("output_schema", [])
        if output_schema:
            sections.append(f"\n{SEP_EXPECTED_OUTPUTS}")
            sections.append("Extract and return the following data points:")
            for field in output_schema:
                if isinstance(field, dict):
                    sections.append(
                        f"- {field.get('key', '')}: {field.get('label', '')}"
                    )

    return CompiledPrompt(
        system_instruction="\n".join(sections),
        temperature=version.temperature,
        max_tokens=version.max_tokens_per_execution,
        version_id=version.id,
        version_number=version.version_number,
        knowledge_file_count=kb_count,
        qualification_question_count=qual_count,
    )
