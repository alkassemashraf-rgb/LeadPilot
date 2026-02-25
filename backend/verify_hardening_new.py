import asyncio
import logging
from uuid import uuid4
from app.core.db import engine
from app.models.models import ZohoLeadMapping, Contact
from app.services.zoho_payload_builder import build_zoho_payload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_hardening():
    # used to be sync session usage here, removing it.
    pass
    
    # Check 1: Unique Constraint
    logger.info("--- 1. Testing Unique Constraint ---")
    ws_id = uuid4()
    
    # We need to manually handle session for async
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.exc import IntegrityError
    
    async with AsyncSession(engine) as session:
        # Create first mapping
        m1 = ZohoLeadMapping(workspace_id=ws_id, field_mappings={"a": "b"})
        session.add(m1)
        await session.commit()
        
        # Create duplicate
        try:
            m2 = ZohoLeadMapping(workspace_id=ws_id, field_mappings={"c": "d"})
            session.add(m2)
            await session.commit()
            logger.error("❌ FAILED: Unique constraint did not prevent duplicate")
        except IntegrityError:
            logger.info("✅ SUCCESS: Unique constraint prevented duplicate")
            await session.rollback()
        except Exception as e:
            logger.error(f"❌ FAILED: Unexpected error: {e}")
            await session.rollback()

    # Check 2: Payload Builder & Description Cap
    logger.info("--- 2. Testing Payload Builder ---")
    async with AsyncSession(engine) as session:
        # User & Contact
        c = Contact(workspace_id=ws_id, first_name="Test", additional_metadata={"notes": "A" * 6000})
        session.add(c)
        await session.commit()
        
        mapping = ZohoLeadMapping(workspace_id=ws_id, field_mappings={"first_name": "First_Name", "description": "Description"})
        
        # Refresh to ensure it's bound
        await session.refresh(c)
        
        payload = await build_zoho_payload(session, c.id, mapping, contact=c)
        
        desc = payload.get("Description")
        if len(desc) <= 5015 and "truncated" in desc: # 5000 + len("... (truncated)")
            logger.info(f"✅ SUCCESS: Description capped. Len: {len(desc)}")
        else:
            logger.error(f"❌ FAILED: Description not capped correctly. Len: {len(desc)}")

if __name__ == "__main__":
    asyncio.run(verify_hardening())
