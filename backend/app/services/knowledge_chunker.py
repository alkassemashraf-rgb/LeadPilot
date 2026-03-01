"""
Knowledge Chunker Service — Mission 29
Handles text chunking for knowledge files and keyword-based retrieval.
"""
import logging
import re
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from app.models.models import KnowledgeChunk

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Common English stopwords to ignore during keyword extraction
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "and", "but", "or", "if", "it",
    "its", "this", "that", "these", "those", "i", "me", "my", "we", "our",
    "you", "your", "he", "him", "his", "she", "her", "they", "them", "their",
    "what", "which", "who", "whom",
})


def chunk_text(text: str) -> List[str]:
    """
    Split text into overlapping chunks, preferring paragraph/sentence boundaries.
    Returns list of chunk strings.
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks: List[str] = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try to break at paragraph boundary
        segment = text[start:end]
        para_break = segment.rfind("\n\n")
        if para_break > CHUNK_SIZE // 3:
            end = start + para_break + 2
        else:
            # Try sentence boundary
            sentence_break = max(
                segment.rfind(". "),
                segment.rfind(".\n"),
                segment.rfind("? "),
                segment.rfind("! "),
            )
            if sentence_break > CHUNK_SIZE // 3:
                end = start + sentence_break + 2

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Advance with overlap
        start = end - CHUNK_OVERLAP if end - CHUNK_OVERLAP > start else end

    return chunks


async def create_chunks_for_file(
    db: AsyncSession,
    workspace_id: UUID,
    file_id: UUID,
    text: str,
) -> int:
    """
    Delete existing chunks for a file, then create new ones from text.
    Returns the number of chunks created.
    """
    # Delete old chunks
    await db.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.knowledge_file_id == file_id,
        )
    )

    chunks = chunk_text(text)
    for i, chunk_content in enumerate(chunks):
        db.add(KnowledgeChunk(
            workspace_id=workspace_id,
            knowledge_file_id=file_id,
            chunk_index=i,
            content_text=chunk_content,
        ))

    await db.flush()
    logger.info("Created %d chunks for file %s", len(chunks), file_id)
    return len(chunks)


def _extract_keywords(text: str, max_keywords: int = 8) -> List[str]:
    """Extract meaningful keywords from text, filtering stopwords."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    seen = set()
    keywords = []
    for w in words:
        if w not in _STOPWORDS and len(w) >= 3 and w not in seen:
            seen.add(w)
            keywords.append(w)
            if len(keywords) >= max_keywords:
                break
    return keywords


async def retrieve_relevant_chunks(
    db: AsyncSession,
    workspace_id: UUID,
    query_text: str,
    max_chunks: int = 8,
) -> List[str]:
    """
    Keyword-based chunk retrieval with recency fallback.
    Returns list of chunk content strings.
    """
    keywords = _extract_keywords(query_text)

    if keywords:
        # Build ILIKE conditions for each keyword
        conditions = []
        for kw in keywords:
            conditions.append(
                KnowledgeChunk.content_text.ilike(f"%{kw}%")
            )

        # Search for chunks matching ANY keyword, order by created_at DESC
        stmt = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.workspace_id == workspace_id,
            )
            .filter(*[
                # Use OR: match any keyword
            ])
        )

        # Build OR condition manually
        from sqlalchemy import or_
        stmt = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.workspace_id == workspace_id,
                or_(*conditions),
            )
            .order_by(KnowledgeChunk.created_at.desc())
            .limit(max_chunks)
        )

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if chunks:
            return [c.content_text for c in chunks]

    # Fallback: most recent chunks regardless of keyword match
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.workspace_id == workspace_id)
        .order_by(KnowledgeChunk.created_at.desc())
        .limit(max_chunks)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    return [c.content_text for c in chunks]
