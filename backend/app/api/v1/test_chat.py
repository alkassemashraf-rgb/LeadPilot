from typing import List, Any, Dict
from pydantic import BaseModel
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc
import json

from app.api import deps
from app.core.db import get_db
from app.models.models import (
    Workspace, PromptConfig, PromptVersion, 
    Conversation, Message, Contact
)
from app.schemas.envelope import ResponseEnvelope, wrap_data, wrap_error
from app.core.ai import ai_provider
from app.core.modules import require_module_enabled, MODULE_RUNTIME_ENGINE

router = APIRouter()

class ChatInput(BaseModel):
    pass # Using raw dict/pydantic later

@router.post("/sessions", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_RUNTIME_ENGINE, "write"))])
async def create_test_session(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Create a new test conversation session."""
    # Create a dummy contact for testing if not exists? 
    # Or just a conversation with platform='test'
    conversation = Conversation(
        workspace_id=workspace.id,
        contact_id=None, # In a real app, create a Contact first
        # platform="test" -- Add this to Conversation model if needed, 
        # but Message has platform.
    )
    # We'll use a specific metadata to flag it as test
    # Actually, let's just use the Message.platform="test"
    
    # Needs a contact though for the foreign key if it's not optional
    # Checking models.py... Conversation has contact_id: UUID = Field(foreign_key="contact.id")
    # I'll create a "Test User" contact for the workspace if missing.
    
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

@router.post("/sessions/{session_id}/messages", response_model=ResponseEnvelope[dict], dependencies=[Depends(require_module_enabled(MODULE_RUNTIME_ENGINE, "write"))])
async def send_test_message(
    session_id: UUID,
    message_in: Dict[str, str], # {"text": "..."}
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
) -> Any:
    """Send a message and get AI response using active PromptConfig."""
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

    # 3. Get active prompt config
    result = await db.execute(
        select(PromptConfig).where(PromptConfig.workspace_id == workspace.id)
    )
    config = result.scalars().first()
    if not config or not config.current_version_id:
        return wrap_error("No active prompt configuration found for this workspace.")

    result = await db.execute(
        select(PromptVersion).where(PromptVersion.id == config.current_version_id)
    )
    version = result.scalars().first()

    # 4. Compile Prompt (System + Profile + Guardrails)
    system_prompt = f"{version.system_prompt_text}\n\n"
    system_prompt += f"BUSINESS PROFILE:\n{json.dumps(version.business_profile_json, indent=2)}\n\n"
    system_prompt += f"GUARDRAILS:\n{json.dumps(version.guardrails_json, indent=2)}"

    # 5. Fetch History (last 10)
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

    # 6. Generate AI Reply
    reply_text = await ai_provider.generate_chat_reply(
        prompt=system_prompt,
        history=history,
        temperature=version.temperature,
        max_tokens=version.max_tokens_per_execution
    )

    # 7. Store assistant message
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
