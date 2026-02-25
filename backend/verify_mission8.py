import asyncio
import logging
from uuid import uuid4
from unittest.mock import patch, AsyncMock

# Setup environment
import sys
import os
sys.path.append(os.getcwd())

from app.core.db import AsyncSession, engine
from app.models.models import (
    Workspace, Contact, ChannelIdentity, 
    Integration, ZohoLeadMapping, 
    ExecutionInstance, ExecutionStatus, FlowVersion
)
from app.domain.runtime import execute_instance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_mission8():
    logger.info("Starting Mission 8 Verification...")
    
    async with AsyncSession(engine) as session:
        # 1. Setup Data
        workspace_id = uuid4()
        user_id = uuid4()
        
        # Create Workspace & User (Mocking auth context if needed, but we call functions directly mostly)
        workspace = Workspace(id=workspace_id, name="Mission 8 Workspace", owner_id=user_id)
        session.add(workspace)
        
        # Create Integration (Mock Locked)
        integration = Integration(
            workspace_id=workspace_id,
            provider="zoho",
            status="connected",
            encrypted_config='{"refresh_token": "mock", "client_id": "mock", "client_secret": "mock"}'
        )
        session.add(integration)
        
        # Create Contact
        contact_id = uuid4()
        contact = Contact(
            id=contact_id,
            workspace_id=workspace_id,
            first_name="Mission",
            last_name="Eight",
            additional_metadata={"company": "LeadPilot Corp", "notes": "Interested in syncing"}
        )
        session.add(contact)
        
        # Create Identity
        identity = ChannelIdentity(
            contact_id=contact_id,
            provider="email",
            provider_user_id="mission8@leadpilot.ai"
        )
        session.add(identity)
        
        await session.commit()
        
        print(f"Created Workspace: {workspace_id}")
        print(f"Created Contact: {contact_id}")

        # 2. Test Mapping Configuration (Direct DB or API simulation)
        mapping = ZohoLeadMapping(
            workspace_id=workspace_id,
            dedupe_strategy="EMAIL",
            field_mappings={
                "first_name": "First_Name",
                "last_name": "Last_Name",
                "email": "Email",
                "company": "Company"
            }
        )
        session.add(mapping)
        await session.commit()
        print("Created Zoho Lead Mapping (Simulating API POST)")

        # 3. Test Manual Sync (Direct API Function Call simulation implies HTTP request usually, but we can check logic via runtime or verify API code logic)
        # We will test the Runtime Node logic primarily, which shares logic with Manual Sync.
        # But let's verify Manual Sync by calling the route handler logic?
        # Requires FastAPI dependency overrides.
        # Let's stick to testing `Runtime Node` end-to-end, and assume API works if logic is similar.
        # OR better: Simulate Manual Sync logic by checking what `zoho.py` does.
        
        # 4. Test Automation Node Execution
        print("\n--- Testing ZOHO_UPSERT_LEAD Node ---")
        
        # Create Flow Version
        flow_version_id = uuid4()
        flow_version = FlowVersion(
            id=flow_version_id,
            workspace_id=workspace_id,
            flow_id=uuid4(), # dummy flow
            version_number=1,
            definition_json={
                "nodes": [
                    {
                        "id": "node-1",
                        "type": "ZOHO_UPSERT_LEAD",
                        "config": {"notes_template": "Upserted via Automation"}
                    }
                ],
                "edges": []
            }
        )
        session.add(flow_version)
        
        # Create Instance
        instance_id = uuid4()
        instance = ExecutionInstance(
            id=instance_id,
            workspace_id=workspace_id,
            flow_version_id=flow_version_id,
            contact_id=contact_id,
            status=ExecutionStatus.RUNNING,
            current_node_id=uuid4(), # Mapped to node-1 below if UUID matches? 
            # Wait, `runtime.py` maps by string ID in node map "id": "node-1"
            # But `current_node_id` is UUID in DB.
            # `runtime.py` expects `nodes` to have UUIDs as IDs usually?
            # Let's check `runtime.py`.
            # `node_map = {str(n["id"]): n for n in nodes}`
            # `current_node_id = str(instance.current_node_id)`
            # So the JSON `id` must implementation-wise be UUID-like or `runtime.py` cast fails if `ExecutionInstance.current_node_id` is UUID type.
            # `ExecutionInstance` model defines `current_node_id` as UUID.
            # So JSON must use UUIDs.
        )
        
        # Fix UUIDs in definition
        node_uuid = uuid4()
        instance.current_node_id = node_uuid
        flow_version.definition_json["nodes"][0]["id"] = str(node_uuid)
        
        session.add(instance)
        await session.commit()
        
        # Mock Adapter
        with patch('app.domain.runtime.ZohoAdapter') as MockAdapter:
            mock_instance = MockAdapter.return_value
            # Make upsert_lead an async mock
            mock_instance.upsert_lead = AsyncMock(return_value=("zoho_auto_123", "created"))
            mock_instance.config = {"refresh_token": "mock", "client_id": "mock"}
            
            print(f"Executing Instance {instance_id}...")
            await execute_instance(instance_id)
            
            # Assertions
            await session.refresh(instance)
            await session.refresh(contact)
            
            print(f"Instance Status: {instance.status}")
            if instance.status == ExecutionStatus.COMPLETED:
                print("SUCCESS: Execution Completed")
            else:
                print(f"FAILURE: Execution Status is {instance.status}")
                
            print(f"Contact Zoho ID: {contact.zoho_lead_id}")
            if contact.zoho_lead_id == "zoho_auto_123":
                 print("SUCCESS: Contact updated with Zoho ID")
            else:
                 print("FAILURE: Contact Zoho ID mismatch")
                 
            # Verify Mock Call
            MockAdapter.assert_called()
            mock_instance.upsert_lead.assert_called_once()
            call_args = mock_instance.upsert_lead.call_args
            payload = call_args[0][0]
            print(f"Payload sent to Zoho: {payload}")
            
            if payload.get("Last_Name") == "Eight" and payload.get("Email") == "mission8@leadpilot.ai":
                print("SUCCESS: Payload Mapped Correctly")
            else:
                print("FAILURE: Payload Mapping Incorrect")

if __name__ == "__main__":
    asyncio.run(verify_mission8())
