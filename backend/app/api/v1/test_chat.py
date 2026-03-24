import logging
from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

logger = logging.getLogger(__name__)

from app.api import deps
from app.core.db import get_db
from app.models.models import Workspace, Conversation, Message, Contact
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.ai import ai_provider
from app.core.modules import require_module_enabled, MODULE_RUNTIME_ENGINE
from app.services.entitlements import require_entitlement
from app.services.prompt_compiler import compile_workspace_prompt

router = APIRouter()


@router.post("/sessions", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_RUNTIME_ENGINE, "write")), Depends(require_entitlement("runtime_engine", increment=True))])
async def create_test_session(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Create a new test conversation session."""
    try:
        result = await db.execute(
            select(Contact).where(Contact.workspace_id == workspace.id, Contact.external_id == "test-contact")
        )
        contact = result.scalars().first()
        if not contact:
            contact = Contact(
                workspace_id=workspace.id,
                external_id="test-contact",
                first_name="Test",
                last_name="User"
            )
            db.add(contact)
            await db.flush()

        conversation = Conversation(
            workspace_id=workspace.id,
            contact_id=contact.id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return wrap_data({"session_id": conversation.id})
    except Exception as exc:
        logger.error("create_test_session failed: %s", exc, exc_info=True)
        return wrap_error(f"Session creation failed: {type(exc).__name__}: {exc}")


@router.post("/sessions/{session_id}/messages", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_RUNTIME_ENGINE, "write")), Depends(require_entitlement("runtime_engine"))])
async def send_test_message(
    session_id: UUID,
    message_in: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Send a message and get AI response using unified prompt compiler."""
    text = message_in.get("text")
    if not text:
        return wrap_error("Message text is required")

    # 1. Fetch conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == session_id, Conversation.workspace_id == workspace.id)
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Store user message
    user_msg = Message(
        workspace_id=workspace.id,
        conversation_id=session_id,
        direction="inbound",
        content=text,
        platform="test"
    )
    db.add(user_msg)
    await db.flush()

    # 3. Compile workspace prompt (includes knowledge chunks + qualification)
    compiled = await compile_workspace_prompt(
        workspace.id, db, include_files=True, include_qualification=True,
        query_hint=text,
    )
    if not compiled.version_id:
        return wrap_error("No active prompt configuration found for this workspace.")

    # 4. Fetch History (last 10)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == session_id)
        .order_by(desc(Message.created_at))
        .limit(10)
    )
    history_objs = result.scalars().all()
    history_objs.reverse()

    history = [
        {"role": "user" if m.direction == "inbound" else "assistant", "content": m.content}
        for m in history_objs
    ]

    # 5. Generate AI Reply
    reply_text = await ai_provider.generate_chat_reply(
        prompt=compiled.system_instruction,
        history=history,
        temperature=compiled.temperature,
        max_tokens=compiled.max_tokens,
    )

    # 6. Store assistant message
    assistant_msg = Message(
        workspace_id=workspace.id,
        conversation_id=session_id,
        direction="outbound",
        content=reply_text,
        platform="test"
    )
    db.add(assistant_msg)
    await db.commit()

    return wrap_data({"reply": reply_text})
