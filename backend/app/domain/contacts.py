import re
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.models import Contact, ChannelIdentity, Conversation


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to digits only.
    Strips +, spaces, dashes, parentheses, dots.
    E.g. "+1 (415) 555-1234" → "14155551234"
    """
    return re.sub(r"[^\d]", "", raw)


async def resolve_or_create_contact(
    session: AsyncSession,
    workspace_id: UUID,
    provider: str,
    provider_user_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> Tuple[Contact, ChannelIdentity, Conversation]:
    """
    Finds or creates a Contact, their ChannelIdentity, and a Conversation.
    """
    # Normalize phone numbers for WhatsApp to prevent duplicates
    if provider == "whatsapp" and provider_user_id:
        provider_user_id = normalize_phone(provider_user_id)

    # 1. Find Identity
    result = await session.execute(
        select(ChannelIdentity).where(
            ChannelIdentity.provider == provider,
            ChannelIdentity.provider_user_id == provider_user_id
        )
    )
    identity = result.scalars().first()
    
    if identity:
        contact = await session.get(Contact, identity.contact_id)
        # Ensure conversation exists
        conv_result = await session.execute(
            select(Conversation).where(
                Conversation.contact_id == contact.id,
                Conversation.workspace_id == workspace_id
            )
        )
        conversation = conv_result.scalars().first()
        if not conversation:
            conversation = Conversation(workspace_id=workspace_id, contact_id=contact.id)
            session.add(conversation)
        else:
            conversation.updated_at = datetime.utcnow()
            session.add(conversation)
        
        await session.flush()
        return contact, identity, conversation

    # 2. Create New Contact
    contact = Contact(
        workspace_id=workspace_id,
        first_name=first_name,
        last_name=last_name
    )
    session.add(contact)
    await session.flush()

    # 3. Create Identity
    identity = ChannelIdentity(
        contact_id=contact.id,
        provider=provider,
        provider_user_id=provider_user_id
    )
    session.add(identity)
    
    # 4. Create Conversation
    conversation = Conversation(
        workspace_id=workspace_id,
        contact_id=contact.id
    )
    session.add(conversation)
    await session.flush()

    return contact, identity, conversation
