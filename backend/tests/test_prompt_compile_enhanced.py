"""
Mission 29: Enhanced Prompt Compilation Tests
Tests qualification criteria, output schema, and chunk retrieval in compiled prompts.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    PromptConfig, PromptVersion,
    QualificationCriterion, KnowledgeChunk,
)
from app.services.prompt_compiler import compile_workspace_prompt


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compile_includes_qualification_criteria(db_session: AsyncSession):
    """Compiled prompt should include qualification criteria section."""
    ws_id = uuid4()

    # Create prompt config + version
    config = PromptConfig(workspace_id=ws_id, name="Test Config")
    db_session.add(config)
    await db_session.flush()

    version = PromptVersion(
        prompt_config_id=config.id,
        version_number=1,
        system_prompt_text="You are a sales assistant.",
        business_profile_json={},
        guardrails_json={},
        structured_data={},
        model="gemini",
        temperature=0.7,
        max_tokens_per_execution=1000,
    )
    db_session.add(version)
    await db_session.flush()
    config.current_version_id = version.id
    await db_session.flush()

    # Add criteria
    db_session.add(QualificationCriterion(
        workspace_id=ws_id,
        code="budget_check",
        label="Budget Above $5K",
        description="Lead stated budget exceeds $5,000",
        criterion_type="boolean",
        is_enabled=True,
        sort_order=0,
    ))
    db_session.add(QualificationCriterion(
        workspace_id=ws_id,
        code="company_size",
        label="Company Size",
        criterion_type="enum",
        enum_values=["small", "medium", "large"],
        is_enabled=True,
        sort_order=1,
    ))
    db_session.add(QualificationCriterion(
        workspace_id=ws_id,
        code="disabled_one",
        label="Disabled Criterion",
        criterion_type="text",
        is_enabled=False,
        sort_order=2,
    ))
    await db_session.flush()

    compiled = await compile_workspace_prompt(ws_id, db_session)

    assert "=== QUALIFICATION CRITERIA ===" in compiled.system_instruction
    assert "Budget Above $5K" in compiled.system_instruction
    assert "Company Size" in compiled.system_instruction
    assert "options: small, medium, large" in compiled.system_instruction
    # Disabled criterion should NOT appear
    assert "Disabled Criterion" not in compiled.system_instruction


@pytest.mark.asyncio
async def test_compile_includes_output_schema(db_session: AsyncSession):
    """Step config with output_schema should add EXPECTED OUTPUTS section."""
    ws_id = uuid4()

    config = PromptConfig(workspace_id=ws_id, name="Test Config")
    db_session.add(config)
    await db_session.flush()

    version = PromptVersion(
        prompt_config_id=config.id,
        version_number=1,
        system_prompt_text="You are a helpful assistant.",
        business_profile_json={},
        guardrails_json={},
        structured_data={},
        model="gemini",
        temperature=0.7,
        max_tokens_per_execution=1000,
    )
    db_session.add(version)
    await db_session.flush()
    config.current_version_id = version.id
    await db_session.flush()

    step_config = {
        "goal": "Collect lead info",
        "tasks": ["Ask for name", "Ask for budget"],
        "output_schema": [
            {"key": "name", "label": "Full Name"},
            {"key": "budget", "label": "Budget Range"},
        ],
    }

    compiled = await compile_workspace_prompt(
        ws_id, db_session, step_config=step_config,
    )

    assert "=== EXPECTED OUTPUTS ===" in compiled.system_instruction
    assert "name: Full Name" in compiled.system_instruction
    assert "budget: Budget Range" in compiled.system_instruction


@pytest.mark.asyncio
async def test_compile_chunk_retrieval(db_session: AsyncSession):
    """When query_hint is provided, should use chunk retrieval."""
    ws_id = uuid4()
    file_id = uuid4()

    config = PromptConfig(workspace_id=ws_id, name="Test Config")
    db_session.add(config)
    await db_session.flush()

    version = PromptVersion(
        prompt_config_id=config.id,
        version_number=1,
        system_prompt_text="You are a helpful assistant.",
        business_profile_json={},
        guardrails_json={},
        structured_data={},
        model="gemini",
        temperature=0.7,
        max_tokens_per_execution=1000,
    )
    db_session.add(version)
    await db_session.flush()
    config.current_version_id = version.id
    await db_session.flush()

    # Add knowledge chunks
    db_session.add(KnowledgeChunk(
        workspace_id=ws_id,
        knowledge_file_id=file_id,
        chunk_index=0,
        content_text="Our premium pricing starts at $500 per month.",
    ))
    db_session.add(KnowledgeChunk(
        workspace_id=ws_id,
        knowledge_file_id=file_id,
        chunk_index=1,
        content_text="Customer support is available 24/7 via phone.",
    ))
    await db_session.flush()

    # Compile with query_hint about pricing
    compiled = await compile_workspace_prompt(
        ws_id, db_session, query_hint="What is the pricing?",
    )

    assert "=== KNOWLEDGE BASE (FILES) ===" in compiled.system_instruction
    assert "pricing" in compiled.system_instruction.lower()
    assert compiled.knowledge_file_count > 0


@pytest.mark.asyncio
async def test_compile_backward_compat_no_query_hint(db_session: AsyncSession):
    """Without query_hint, should still work (backward compat)."""
    ws_id = uuid4()

    config = PromptConfig(workspace_id=ws_id, name="Test Config")
    db_session.add(config)
    await db_session.flush()

    version = PromptVersion(
        prompt_config_id=config.id,
        version_number=1,
        system_prompt_text="You are a helpful assistant.",
        business_profile_json={},
        guardrails_json={},
        structured_data={},
        model="gemini",
        temperature=0.7,
        max_tokens_per_execution=1000,
    )
    db_session.add(version)
    await db_session.flush()
    config.current_version_id = version.id
    await db_session.flush()

    # Should not raise
    compiled = await compile_workspace_prompt(ws_id, db_session)
    assert "You are a helpful assistant." in compiled.system_instruction
