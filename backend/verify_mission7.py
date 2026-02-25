import asyncio
import uuid
from uuid import UUID
from app.core.db import SessionLocal
from app.models.models import (
    Message, 
    DeliveryStatus, 
    ConversationStatus, 
    ExecutionInstance,
    ExecutionStatus
)
from app.domain.contacts import resolve_or_create_contact
from app.domain.runtime import execute_instance

async def verify_mission_7():
    async with SessionLocal() as db:
        workspace_id = UUID("6b58dc0e-b1e7-480e-bd67-d872bdaf9a24")
        provider = "whatsapp"
        provider_user_id = f"test_user_{uuid.uuid4().hex[:6]}"
        
        print("--- 1. Testing Inbound Resolution & Conversation Creation ---")
        contact, identity, conv = await resolve_or_create_contact(
            db, workspace_id, provider, provider_user_id, first_name="Mission7", last_name="Tester"
        )
        # resolve_or_create_contact is sync wrapper in our code usually? 
        # Wait, the file I saw was sync? Yes, from app.domain.contacts import ...
        # Let's check imports in contacts.py: from sqlmodel import Session (Sync)
        
        print(f"Created Contact: {contact.id}")
        print(f"Created/Resolved Conversation: {conv.id} - Status: {conv.status}")
        
        # Verify updated_at logic
        old_updated_at = conv.updated_at
        await asyncio.sleep(1)
        _, _, conv_refreshed = await resolve_or_create_contact(
            db, workspace_id, provider, provider_user_id
        )
        print(f"Conversation refreshed. Updated? {conv_refreshed.updated_at > old_updated_at}")

        print("\n--- 2. Testing Human Takeover Guard ---")
        # Set to HUMAN_TAKEOVER
        conv.status = ConversationStatus.HUMAN_TAKEOVER
        db.add(conv)
        await db.commit()
        
        # Try to run an execution instance
        dummy_instance = ExecutionInstance(
            workspace_id=workspace_id,
            contact_id=contact.id,
            flow_version_id=uuid.uuid4(), # Dummy
            status=ExecutionStatus.RUNNING,
            current_node_id=uuid.uuid4()
        )
        db.add(dummy_instance)
        await db.commit()
        
        print(f"Triggering execution for instance {dummy_instance.id} (Conversation is {conv.status})...")
        await execute_instance(dummy_instance.id)
        
        await db.refresh(dummy_instance)
        print(f"Instance status after execution: {dummy_instance.status} (Expected: aborted)")
        print(f"Abort Reason: {dummy_instance.abort_reason}")

        print("\n--- 3. Testing Manual Reply Flow ---")
        # Manual reply (Simulated from Inbox API)
        manual_msg = Message(
            workspace_id=workspace_id,
            conversation_id=conv.id,
            direction="outbound",
            platform=provider,
            content="Manual Reply from Inbox",
            delivery_status=DeliveryStatus.PENDING,
            is_outbound_intent=True
        )
        db.add(manual_msg)
        await db.commit()
        print(f"Stored Manual Message: {manual_msg.id}")
        
        # Verify it picks up during dispatch
        from app.services.dispatch_service import DispatchService
        # For dispatch_message, we need an AsyncSession
        from app.core.db import SessionLocal as AsyncSessionLocal # Wait, backend/app/core/db.py says SessionLocal is async
        
        async with AsyncSessionLocal() as adb:
            msg_to_send = await adb.get(Message, manual_msg.id)
            # Mock provider call success by just checking if it gets to sending status
            # we don't have real credentials here, so it will fail provider check which is fine for logic verification
            try:
                await DispatchService.dispatch_message(adb, msg_to_send)
            except Exception as e:
                print(f"Dispatch (expectedly) failed provider call: {e}")
            
            await adb.refresh(msg_to_send)
            print(f"Message status: {msg_to_send.delivery_status}")

if __name__ == "__main__":
    asyncio.run(verify_mission_7())
