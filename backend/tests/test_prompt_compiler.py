"""Tests for Prompt Compiler Service — Mission 20."""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Workspace,
    PromptConfig,
    PromptVersion,
    WorkspaceKnowledgeFile,
    QualificationConfig,
)
from app.services.prompt_compiler import compile_workspace_prompt


@pytest_asyncio.fixture
async def compiler_workspace(db_session: AsyncSession):
    """Create a workspace with prompt config, knowledge files, and qualification config."""
    ws = Workspace(id=uuid4(), name="Compiler Test WS")
    db_session.add(ws)
    await db_session.flush()

    # Create PromptConfig first (version needs prompt_config_id)
    config = PromptConfig(
        id=uuid4(),
        workspace_id=ws.id,
        current_version_id=None,  # Will update after version created
    )
    db_session.add(config)
    await db_session.flush()

    # Prompt version
    version = PromptVersion(
        id=uuid4(),
        prompt_config_id=config.id,
        version_number=1,
        system_prompt_text="You are a helpful sales assistant.",
        structured_data={},
        compiled_system_instruction="You are a helpful sales assistant.",
        business_profile_json={"company": "Acme Corp", "industry": "Tech"},
        guardrails_json={"never_do": ["make up pricing"]},
        model="gemini-pro",
        temperature=0.8,
        max_tokens_per_execution=500,
    )
    db_session.add(version)
    await db_session.flush()

    # Update config to point to this version
    config.current_version_id = version.id

    # Knowledge files
    kf1 = WorkspaceKnowledgeFile(
        id=uuid4(),
        workspace_id=ws.id,
        filename="pricing.txt",
        mime_type="text/plain",
        size_bytes=100,
        storage_path="/tmp/fake.txt",
        extracted_text="Our basic plan costs $99/month.",
        status="READY",
        sha256_hash="abc123",
    )
    kf2 = WorkspaceKnowledgeFile(
        id=uuid4(),
        workspace_id=ws.id,
        filename="faq.txt",
        mime_type="text/plain",
        size_bytes=50,
        storage_path="/tmp/fake2.txt",
        extracted_text="We support WhatsApp and email.",
        status="READY",
        sha256_hash="def456",
    )
    kf_failed = WorkspaceKnowledgeFile(
        id=uuid4(),
        workspace_id=ws.id,
        filename="broken.pdf",
        mime_type="application/pdf",
        size_bytes=200,
        storage_path="/tmp/fake3.pdf",
        extracted_text=None,
        status="FAILED",
        sha256_hash="ghi789",
    )
    db_session.add_all([kf1, kf2, kf_failed])

    # Qualification config
    qual = QualificationConfig(
        id=uuid4(),
        workspace_id=ws.id,
        version=1,
        qualification_questions=[
            {"label": "Full Name", "enabled": True, "order": 0},
            {"label": "Budget Range", "enabled": True, "order": 1},
            {"label": "Disabled Q", "enabled": False, "order": 2},
        ],
        qualification_statuses=[
            {"label": "New", "color": "#94a3b8", "enabled": True},
        ],
    )
    db_session.add(qual)
    await db_session.flush()

    return ws


@pytest.mark.asyncio
async def test_compiler_includes_all_sections(db_session: AsyncSession, compiler_workspace):
    """Compiler output includes prompt text, business profile, guardrails, files, qualification."""
    ws = compiler_workspace
    compiled = await compile_workspace_prompt(ws.id, db_session)

    si = compiled.system_instruction

    # Core prompt
    assert "You are a helpful sales assistant." in si

    # Business profile
    assert "=== BUSINESS PROFILE ===" in si
    assert "Acme Corp" in si

    # Guardrails
    assert "=== GUARDRAILS ===" in si
    assert "make up pricing" in si

    # Knowledge files (only READY with extracted_text)
    assert "=== KNOWLEDGE BASE (FILES) ===" in si
    assert "pricing.txt" in si
    assert "$99/month" in si
    assert "faq.txt" in si
    assert "WhatsApp" in si
    # FAILED file should NOT appear
    assert "broken.pdf" not in si

    # Qualification (only enabled questions)
    assert "=== LEAD QUALIFICATION ===" in si
    assert "Full Name" in si
    assert "Budget Range" in si
    assert "Disabled Q" not in si

    # Metadata
    assert compiled.knowledge_file_count == 2
    assert compiled.qualification_question_count == 2
    assert compiled.temperature == 0.8
    assert compiled.max_tokens == 500


@pytest.mark.asyncio
async def test_compiler_with_step_config(db_session: AsyncSession, compiler_workspace):
    """Compiler appends step-level config when provided."""
    ws = compiler_workspace
    step_config = {
        "goal": "Schedule a demo call",
        "tasks": ["Ask for preferred date", "Confirm timezone"],
        "extra_instructions": "Be concise and direct.",
    }
    compiled = await compile_workspace_prompt(
        ws.id, db_session, step_config=step_config
    )

    si = compiled.system_instruction
    assert "=== STEP GOAL ===" in si
    assert "Schedule a demo call" in si
    assert "=== TASKS ===" in si
    assert "Ask for preferred date" in si
    assert "Confirm timezone" in si
    assert "=== STEP INSTRUCTIONS ===" in si
    assert "Be concise and direct." in si


@pytest.mark.asyncio
async def test_compiler_without_files(db_session: AsyncSession, compiler_workspace):
    """With include_files=False, knowledge base section is omitted."""
    ws = compiler_workspace
    compiled = await compile_workspace_prompt(
        ws.id, db_session, include_files=False
    )

    si = compiled.system_instruction
    assert "=== KNOWLEDGE BASE (FILES) ===" not in si
    assert compiled.knowledge_file_count == 0
    # Other sections still present
    assert "=== BUSINESS PROFILE ===" in si


@pytest.mark.asyncio
async def test_compiler_without_qualification(db_session: AsyncSession, compiler_workspace):
    """With include_qualification=False, qualification section is omitted."""
    ws = compiler_workspace
    compiled = await compile_workspace_prompt(
        ws.id, db_session, include_qualification=False
    )

    si = compiled.system_instruction
    assert "=== LEAD QUALIFICATION ===" not in si
    assert compiled.qualification_question_count == 0


@pytest.mark.asyncio
async def test_compiler_no_config_returns_default(db_session: AsyncSession):
    """Workspace with no PromptConfig returns a sensible default."""
    ws = Workspace(id=uuid4(), name="Empty WS")
    db_session.add(ws)
    await db_session.flush()

    compiled = await compile_workspace_prompt(ws.id, db_session)
    assert compiled.system_instruction == "You are a helpful assistant."
    assert compiled.temperature == 0.7
    assert compiled.max_tokens == 1000
