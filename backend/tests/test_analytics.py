import pytest
from httpx import AsyncClient

async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "Analytics Test"})
    login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

@pytest.mark.asyncio
async def test_analytics_envelope(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "analytics_test@example.com")
    
    res = await async_client.get("/api/v1/analytics/summary", headers=headers)
    if res.status_code != 200:
        print(f"FAILED: {res.text}")
    assert res.status_code == 200
    
    json_data = res.json()
    
    # Verify ResponseEnvelope structure
    assert "success" in json_data
    assert "data" in json_data
    assert "error" in json_data
    
    assert json_data["success"] is True
    assert json_data["error"] is None
    
    # Verify Data keys
    data = json_data["data"]
    expected_keys = [
        "conversations_count", 
        "new_contacts_count", 
        "inbound_messages_count",
        "execution_completed_count"
    ]
    for key in expected_keys:
        assert key in data
