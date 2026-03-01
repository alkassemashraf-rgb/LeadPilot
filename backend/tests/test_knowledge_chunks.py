"""
Mission 29: Knowledge Chunks Tests
Tests file upload creates chunks, cascade delete, and chunk retrieval.
"""
import io
import pytest
import pytest_asyncio
from typing import Optional
from uuid import UUID, uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.models import (
    Workspace, WorkspaceMember, SystemModuleConfig, KnowledgeChunk,
)
from app.core.modules import module_cache
from app.services.knowledge_chunker import chunk_text, retrieve_relevant_chunks


# ── Helpers ─────────────────────────────────────────────────────────


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "KB User",
    })
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "securepassword123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    return login.json()["data"]["access_token"]


def _auth(token: str, workspace_id: Optional[str] = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-ID"] = workspace_id
    return headers


@pytest.fixture(autouse=True)
def clear_module_cache():
    module_cache._cache.clear()
    yield
    module_cache._cache.clear()


@pytest_asyncio.fixture
async def kb_setup(async_client: AsyncClient, db_session: AsyncSession):
    """Create user + workspace + modules for knowledge tests."""
    token = await _signup_and_login(async_client, "kbchunk@example.com")

    ws = Workspace(id=uuid4(), name="KB Chunk WS", subscription_tier="free")
    db_session.add(ws)

    me_res = await async_client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = UUID(me_res.json()["data"]["id"])

    member = WorkspaceMember(user_id=user_id, workspace_id=ws.id, role="owner")
    db_session.add(member)

    for mod in ["knowledge_files", "prompt_studio"]:
        db_session.add(SystemModuleConfig(module_name=mod, is_enabled=True))

    await db_session.flush()
    return {"token": token, "workspace": ws}


# ── Unit Tests: chunk_text ─────────────────────────────────────────


def test_chunk_text_short():
    """Short text should return a single chunk."""
    result = chunk_text("Hello world")
    assert len(result) == 1
    assert result[0] == "Hello world"


def test_chunk_text_empty():
    """Empty text should return empty list."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_long():
    """Long text should be split into multiple chunks."""
    text = "A" * 3000
    chunks = chunk_text(text)
    assert len(chunks) > 1
    # All original text should be covered
    total = sum(len(c) for c in chunks)
    # Due to overlap, total chars > original but all content is covered
    assert total >= 3000


def test_chunk_text_paragraph_boundaries():
    """Chunks should prefer paragraph boundaries."""
    text = ("First paragraph. " * 30) + "\n\n" + ("Second paragraph. " * 30)
    chunks = chunk_text(text)
    assert len(chunks) >= 2


# ── Integration Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_creates_chunks(async_client: AsyncClient, kb_setup, db_session: AsyncSession):
    setup = kb_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    file_content = b"This is a test knowledge file with important pricing information.\n" * 20

    response = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["extracted"] is True
    assert data["data"]["chunk_count"] > 0

    # Verify chunks in DB
    file_id = UUID(data["data"]["id"])
    result = await db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == file_id)
    )
    chunks = result.scalars().all()
    assert len(chunks) == data["data"]["chunk_count"]
    assert all(c.workspace_id == setup["workspace"].id for c in chunks)


@pytest.mark.asyncio
async def test_delete_cascades_chunks(async_client: AsyncClient, kb_setup, db_session: AsyncSession):
    setup = kb_setup
    headers = _auth(setup["token"], str(setup["workspace"].id))

    file_content = b"Some content for cascade test.\n" * 10

    # Upload
    upload_res = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("cascade.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    file_id = upload_res.json()["data"]["id"]

    # Verify chunks exist
    result = await db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == UUID(file_id))
    )
    assert len(result.scalars().all()) > 0

    # Delete file
    del_res = await async_client.delete(f"/api/v1/knowledge/files/{file_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify chunks deleted
    result = await db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.knowledge_file_id == UUID(file_id))
    )
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_chunk_retrieval_keyword(db_session: AsyncSession):
    """Test keyword-based chunk retrieval."""
    ws_id = uuid4()
    file_id = uuid4()

    # Create test chunks
    chunks_data = [
        "Our premium pricing starts at $500 per month for the basic plan.",
        "Customer support is available 24/7 via phone and email.",
        "The enterprise plan includes advanced analytics and reporting.",
        "Our team has over 10 years of experience in marketing automation.",
    ]
    for i, text in enumerate(chunks_data):
        db_session.add(KnowledgeChunk(
            workspace_id=ws_id,
            knowledge_file_id=file_id,
            chunk_index=i,
            content_text=text,
        ))
    await db_session.flush()

    # Search for pricing-related content
    results = await retrieve_relevant_chunks(db_session, ws_id, "What is the pricing?")
    assert len(results) > 0
    assert any("pricing" in r.lower() for r in results)
