import pytest
from httpx import AsyncClient

async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "Inbox Test"})
    login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

@pytest.mark.asyncio
async def test_automation_publish(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "auto_test@example.com")
    
    # Must use /from-builder 
    flow_payload = {
        "name": "Test Flow",
        "description": "Integration test flow",
        "steps": [], 
        "trigger": {"type": "MESSAGE_INBOUND", "platform": "WHATSAPP", "keywords": []},
        "publish": False
    }
    start_res = await async_client.post("/api/v1/automations/from-builder", json=flow_payload, headers=headers)
    assert start_res.status_code == 200, f"Create Failed: {start_res.text}"
    flow_data = start_res.json()["data"]
    flow_id = flow_data["flow_id"]
    
    # 2. Publish
    pub_payload = {
        "definition": {"nodes": [], "edges": []},
        "system_prompt": "You are a test bot",
        "commit_message": "Initial publish"
    }
    
    pub_res = await async_client.post(f"/api/v1/automations/{flow_id}/publish", json=pub_payload, headers=headers)
    assert pub_res.status_code == 200, f"Publish Failed: {pub_res.text}"
    version_data = pub_res.json()["data"]
    assert version_data["status"] == "published"
