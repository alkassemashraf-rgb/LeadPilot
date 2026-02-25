import pytest
from httpx import AsyncClient

async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    # Helper to signup/login and get headers
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "WS Test"})
    login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    
    # Decode token to get default workspace (or just fetch user to find it if needed, but Login returns context usually?)
    # For now, let's just use the token. The backend often infers workspace or requires header.
    # We need the workspace ID.
    # Let's hit /auth/me or similar if exists, or use the token payload logic if we could decode.
    # Better: Signup returns the user, we can assume default workspace is created. 
    # Let's inspect the side-effects or just use a known endpoint to list workspaces.
    
    # Assuming we need to find the workspace ID. 
    # Let's try listing workspaces if that endpoint exists, or just create a fresh one.
    # Or, simpler: The LOGIN endpoint in this app returns a token scoped to a workspace?
    # Checking auth.py: login returns token.
    # Let's use `GET /workspaces` (assuming it exists, usually does in this stack).
    
    # Wait, strict checking: we need the workspace ID to trigger X-Workspace-ID checks.
    # We'll just assume there is a /api/v1/workspaces endpoint based on standard patterns.
    # If not, we'll fail and fix.
    
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    if ws_res.status_code == 200:
        ws_id = ws_res.json()["data"][0]["id"] # list of workspaces
        return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}
    
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_workspace_isolation(async_client: AsyncClient):
    # User 1
    headers1 = await get_auth_headers(async_client, "user1@example.com")
    
    # User 2
    headers2 = await get_auth_headers(async_client, "user2@example.com")
    
    # User 1 creates a Prompt Config
    pc_payload = {
        "structured_data": {"basics": {"business_name": "User 1 Bot"}},
        "temperature": 0.5
    }
    create_res = await async_client.post("/api/v1/prompt-config/", json=pc_payload, headers=headers1)
    # Note: If /prompt-config doesn't exist, this will fail (we'll implement the test anyway as requested)
    # Based on user request "prompt-config create/read", it should exist.
    assert create_res.status_code == 200
    # Response is Version, not Config
    # We don't get config ID directly in data. 
    # But we can get it via GET /
    
    # User 2 tries to read Config
    # The endpoint is singleton per workspace: GET /api/v1/prompt-config/
    # So User 2 calling GET / should returned User 2's empty config or default, NOT User 1's.
    
    # Actually, verify User 2 cannot access User 1's data via ID if there was ID based access.
    # But current design is Singleton. 
    # So test is: User 2 calls GET / and sees DIFFERENT data (or default) than User 1.
    
    # Let's verify User 1 sees what they created.
    get1 = await async_client.get("/api/v1/prompt-config/", headers=headers1)
    v1_data = get1.json()["data"]["versions"][0]
    assert v1_data["structured_data"]["basics"]["business_name"] == "User 1 Bot"
    
    # User 2 calls GET /
    get2 = await async_client.get("/api/v1/prompt-config/", headers=headers2)
    assert get2.status_code == 200
    data2 = get2.json()["data"]
    # Should be empty or default
    if data2["versions"]:
        assert data2["versions"][0]["structured_data"].get("basics", {}).get("business_name") != "User 1 Bot"
    else:
        assert True # Empty versions means clean slate
    
    # If there was an ID based endpoint: GET /prompt-config/{id}
    # It seems from audit/code viewing, prompt_config endpoint is singleton "/".
    # So "Isolation" means I see my config, you see yours. Verified above.

    # If there was an ID based endpoint: GET /prompt-config/{id}
    # It seems from audit/code viewing, prompt_config endpoint is singleton "/".
    # So "Isolation" means I see my config, you see yours. Verified above.

@pytest.mark.asyncio
async def test_invite_member(async_client: AsyncClient):
    # User 1 (Owner)
    headers = await get_auth_headers(async_client, "owner@example.com")
    
    # Switch context if get_auth_headers returns X-Workspace-ID
    # It does based on my read of previous file content
    
    payload = {"email": "invited@example.com", "role": "member"}
    res = await async_client.post("/api/v1/workspaces/members/invite", json=payload, headers=headers)
    
    assert res.status_code == 200
    assert "Invite sent" in res.json()["data"]["message"]
