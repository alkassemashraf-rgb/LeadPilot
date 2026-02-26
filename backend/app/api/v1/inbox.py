from typing import Any, List, Optional
from uuid import UUID
from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, and_, or_, col, desc

from app.api import deps
from app.core.db import get_db
from app.models.models import (
    Conversation, 
    Message, 
    Contact, 
    DeliveryStatus, 
    ConversationStatus, 
    Workspace
)
from app.schemas.envelope import ResponseEnvelope, wrap_data
from app.services.dispatch_service import DispatchService
from app.workers.tasks import dispatch_message_task
from app.services.entitlements import require_entitlement

router = APIRouter()


@router.get("/conversations", response_model=ResponseEnvelope[List[dict]], dependencies=[Depends(require_entitlement("inbox"))])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member", "viewer"])),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[ConversationStatus] = None,
    platform: Optional[str] = None,
    q: Optional[str] = None
) -> Any:
    """
    List conversations for the workspace with pagination and filters.
    Sorted by last_message_at DESC.
    """
    offset = (page - 1) * limit
    
    # Base Query
    query = select(Conversation).where(Conversation.workspace_id == workspace.id)
    
    # Filter by Status
    if status:
        query = query.where(Conversation.status == status)
    
    # Filter by Contact Name or Platform (requires join)
    if q or platform:
        query = query.join(Contact, isouter=True)
        if q:
            search = f"%{q}%"
            query = query.where(
                or_(
                    col(Contact.display_name).ilike(search),
                    col(Contact.first_name).ilike(search),
                    col(Contact.last_name).ilike(search)
                )
            )
        if platform:
            # Platform is usually resolved via identities, but for now we look at the last message platform
            # or we can join ChannelIdentity if needed. Let's simplify for MVP.
            pass

    query = query.order_by(desc(Conversation.last_message_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    items = []
    for conv in conversations:
        # Fetch contact
        contact = await db.get(Contact, conv.contact_id)
        
        # Fetch last message preview
        msg_query = select(Message).where(Message.conversation_id == conv.id).order_by(desc(Message.created_at)).limit(1)
        last_msg = (await db.execute(msg_query)).scalars().first()
        
        items.append({
            "conversation_id": str(conv.id),
            "contact": {
                "id": str(contact.id),
                "display_name": contact.display_name or f"{contact.first_name or ''} {contact.last_name or ''}".strip() or "Unknown Contact"
            },
            "last_message_preview": last_msg.content[:100] if last_msg else None,
            "platform": last_msg.platform if last_msg else "unknown",
            "status": conv.status,
            "updated_at": conv.updated_at,
            "unread_count": 0 # MVP
        })
        
    return wrap_data(items)

@router.get("/conversations/{conversation_id}", response_model=ResponseEnvelope[dict])
async def get_conversation_thread(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member", "viewer"]))
) -> Any:
    """
    Get full thread history for a conversation.
    """
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    contact = await db.get(Contact, conv.contact_id)
    
    # Fetch last 100 messages
    msg_query = select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc()).limit(100)
    messages = (await db.execute(msg_query)).scalars().all()
    
    return wrap_data({
        "conversation_id": str(conv.id),
        "status": conv.status,
        "contact": {
            "id": str(contact.id),
            "display_name": contact.display_name or f"{contact.first_name or ''} {contact.last_name or ''}".strip() or "Unknown Contact"
        },
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "content": m.content,
                "platform": m.platform,
                "created_at": m.created_at,
                "delivery_status": m.delivery_status,
                "last_error": m.last_error
            } for m in messages
        ]
    })

@router.post("/conversations/{conversation_id}/reply", response_model=ResponseEnvelope[dict])
async def reply_to_conversation(
    conversation_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member"]))
) -> Any:
    """
    Manually reply to a conversation.
    """
    content = body.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
        
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if conv.status == ConversationStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot reply to a closed conversation")

    # Resolve platform from last message or identities
    last_msg_query = select(Message).where(Message.conversation_id == conv.id).order_by(desc(Message.created_at)).limit(1)
    last_msg = (await db.execute(last_msg_query)).scalars().first()
    platform = last_msg.platform if last_msg else "unknown"

    # Compute Idempotency Hash (Last 10 minutes)
    # We need recipient_id here, but we can rely on DispatchService to handle it if we just provide the message.
    # Actually, runtime.py computes it before storage. Let's be consistent.
    # For now, we skip hash here and let DispatchService guard by provider_id if it exists.
    # Or we can compute a simple hash of (conv_id, content, now_bucket)
    
    new_msg = Message(
        workspace_id=workspace.id,
        conversation_id=conv.id,
        direction="outbound",
        content=content,
        platform=platform,
        delivery_status=DeliveryStatus.PENDING,
        is_outbound_intent=True
    )
    db.add(new_msg)
    
    # Update conversation updated_at
    conv.updated_at = datetime.utcnow()
    db.add(conv)
    
    await db.commit()
    await db.refresh(new_msg)
    
    # Enqueue dispatch
    dispatch_message_task.delay(str(new_msg.id))
    
    return wrap_data({"message_id": str(new_msg.id), "status": "pending"})

@router.patch("/conversations/{conversation_id}/status", response_model=ResponseEnvelope[dict])
async def update_conversation_status(
    conversation_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(deps.get_active_workspace),
    _ = Depends(deps.require_role(["owner", "member"]))
) -> Any:
    """
    Toggle between BOT_ACTIVE, HUMAN_TAKEOVER, and CLOSED.
    """
    new_status = body.get("status")
    if not new_status or new_status not in [s.value for s in ConversationStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    conv.status = ConversationStatus(new_status)
    conv.updated_at = datetime.utcnow()
    db.add(conv)
    await db.commit()
    
    return wrap_data({"conversation_id": str(conv.id), "status": conv.status})
