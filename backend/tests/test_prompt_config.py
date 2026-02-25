import pytest
from httpx import AsyncClient

# Reusing the helper from test_workspaces would be good, but for speed/isolation repeating setup logic or moving to conftest later.
# For now, minimal inline setup.

async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "Config Test"})
    login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}

@pytest.mark.asyncio
async def test_prompt_config_lifecycle(async_client: AsyncClient):
    headers = await get_auth_headers(async_client, "config_test@example.com")
    
    # 1. Create
    payload = {
        "structured_data": {
            "basics": {"business_name": "Sales Bot"},
            "behavior": {"tone": "Professional", "assistant_role": "Sales Rep"},
            "qualification": {"required_details": []},
            "pricing": {}
        },
        "temperature": 0.7,
        "max_tokens_per_execution": 1000
    }
    res = await async_client.post("/api/v1/prompt-config/", json=payload, headers=headers)
    assert res.status_code == 200
    version_data = res.json()["data"]
    # POST / returns PromptVersionRead, not Config
    assert "id" in version_data
    assert version_data["version_number"] >= 1
    
    # 2. Read Config (GET /)
    res = await async_client.get("/api/v1/prompt-config/", headers=headers)
    assert res.status_code == 200
    config_data = res.json()["data"]
    assert len(config_data["versions"]) > 0
    assert "compiled_system_instruction" in config_data["versions"][0]
    
    # 3. Update (if endpoint exists/implemented)
    # Skipping explicitly requested "create/read" in user prompt, but CRUD usually implies Update.
    # We will stick to Create/Read per strict requirements: "prompt-config create/read per workspace isolation"
