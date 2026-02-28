"""
Integration tests for the automation endpoints (Mission 27 — Builder v2).

Tests cover:
- Backward compatibility of /from-builder
- Blank flow creation
- Draft get/save/validate
- Publish (validation gate, FlowVersion creation, published_version_id)
- Version listing with is_active flag
- Rollback (creates new version = old snapshot)
- Simulate (dry-run, no dispatch)
"""
import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_BUILDER_GRAPH = {
    "nodes": [
        {
            "id": "trigger-1",
            "type": "triggerNode",
            "position": {"x": 250, "y": 50},
            "data": {"nodeType": "MESSAGE_INBOUND", "platform": "whatsapp", "config": {}},
        },
        {
            "id": "node-1",
            "type": "actionNode",
            "position": {"x": 250, "y": 220},
            "data": {"nodeType": "AI_REPLY", "config": {"goal": "Help the user", "tasks": []}},
        },
    ],
    "edges": [{"id": "e1", "source": "trigger-1", "target": "node-1"}],
}

INVALID_BUILDER_GRAPH = {
    "nodes": [
        {
            "id": "trigger-1",
            "type": "triggerNode",
            "position": {"x": 250, "y": 50},
            "data": {"nodeType": "MESSAGE_INBOUND", "platform": "whatsapp", "config": {}},
        },
        {
            "id": "node-1",
            "type": "actionNode",
            "position": {"x": 250, "y": 220},
            "data": {"nodeType": "AI_REPLY", "config": {"goal": ""}},  # missing goal
        },
    ],
    "edges": [{"id": "e1", "source": "trigger-1", "target": "node-1"}],
}


async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "Auto Test"})
    login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = login_res.json()["data"]["access_token"]
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


async def create_blank_flow(client: AsyncClient, headers: dict, name: str = "Test Flow") -> str:
    """Helper: create blank flow, return flow_id."""
    res = await client.post("/api/v1/automations", json={"name": name}, headers=headers)
    assert res.status_code == 200, f"Create flow failed: {res.text}"
    return res.json()["data"]["flow_id"]


async def save_draft(client: AsyncClient, headers: dict, flow_id: str, graph: dict) -> None:
    """Helper: save draft."""
    res = await client.put(
        f"/api/v1/automations/{flow_id}/draft",
        json={"builder_graph_json": graph},
        headers=headers,
    )
    assert res.status_code == 200, f"Save draft failed: {res.text}"


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_from_builder_backward_compat(async_client: AsyncClient):
    """POST /from-builder with publish=True still works (backward compat)."""
    headers = await get_auth_headers(async_client, "compat_test@example.com")

    payload = {
        "name": "Compat Flow",
        "description": "Backward compat test",
        "steps": [],
        "trigger": {"type": "MESSAGE_INBOUND", "platform": "WHATSAPP", "keywords": []},
        "publish": True,
    }
    res = await async_client.post("/api/v1/automations/from-builder", json=payload, headers=headers)
    assert res.status_code == 200, f"from-builder failed: {res.text}"
    data = res.json()["data"]
    assert "flow_id" in data
    assert data["version"] == 1


# ---------------------------------------------------------------------------
# Flow Creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_blank_flow(async_client: AsyncClient):
    """POST /automations creates a blank DRAFT flow and returns flow_id."""
    headers = await get_auth_headers(async_client, "blank_flow@example.com")
    res = await async_client.post("/api/v1/automations", json={"name": "My Canvas Flow"}, headers=headers)
    assert res.status_code == 200
    assert "flow_id" in res.json()["data"]


# ---------------------------------------------------------------------------
# Draft — Get / Save
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_draft_empty(async_client: AsyncClient):
    """GET /draft on a new flow returns builder_graph_json=null."""
    headers = await get_auth_headers(async_client, "draft_empty@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    res = await async_client.get(f"/api/v1/automations/{flow_id}/draft", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["builder_graph_json"] is None
    assert data["last_validation_errors"] is None


@pytest.mark.asyncio
async def test_put_and_get_draft(async_client: AsyncClient):
    """PUT draft then GET returns the same builder_graph_json."""
    headers = await get_auth_headers(async_client, "draft_save@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    res = await async_client.get(f"/api/v1/automations/{flow_id}/draft", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["builder_graph_json"] is not None
    assert len(data["builder_graph_json"]["nodes"]) == 2
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_put_draft_twice_upserts(async_client: AsyncClient):
    """Saving draft twice updates in-place (no duplicate rows)."""
    headers = await get_auth_headers(async_client, "draft_upsert@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    updated_graph = dict(VALID_BUILDER_GRAPH)
    updated_graph["nodes"] = [VALID_BUILDER_GRAPH["nodes"][0]]  # only trigger
    updated_graph["edges"] = []
    await save_draft(async_client, headers, flow_id, updated_graph)

    res = await async_client.get(f"/api/v1/automations/{flow_id}/draft", headers=headers)
    draft = res.json()["data"]["builder_graph_json"]
    assert len(draft["nodes"]) == 1  # reflects second save


# ---------------------------------------------------------------------------
# Draft — Validate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_draft_no_draft_returns_error(async_client: AsyncClient):
    """Validate without a saved draft returns error message."""
    headers = await get_auth_headers(async_client, "validate_nodraft@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/draft/validate", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_validate_draft_invalid(async_client: AsyncClient):
    """Validate draft with missing AI_REPLY goal returns structured errors."""
    headers = await get_auth_headers(async_client, "validate_invalid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, INVALID_BUILDER_GRAPH)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/draft/validate", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True  # request succeeded, validation failed
    data = body["data"]
    assert data["valid"] is False
    assert len(data["errors"]) >= 1
    assert any(e["node_id"] == "node-1" for e in data["errors"])


@pytest.mark.asyncio
async def test_validate_draft_valid(async_client: AsyncClient):
    """Validate draft with correct graph returns valid=True and no errors."""
    headers = await get_auth_headers(async_client, "validate_valid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/draft/validate", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is True
    assert data["errors"] == []


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_without_draft_fails(async_client: AsyncClient):
    """Publish without a draft returns an error (not 500)."""
    headers = await get_auth_headers(async_client, "publish_nodraft@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_publish_invalid_draft_blocked(async_client: AsyncClient):
    """Publish with invalid draft does NOT create a FlowVersion. Returns errors."""
    headers = await get_auth_headers(async_client, "publish_invalid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, INVALID_BUILDER_GRAPH)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is False
    assert data["published"] is False
    assert len(data["errors"]) >= 1


@pytest.mark.asyncio
async def test_publish_valid_creates_flow_version(async_client: AsyncClient):
    """
    Valid draft publish:
    - Creates FlowVersion
    - Sets flow.published_version_id
    - Returns success=True + version_number
    - Flow status becomes PUBLISHED
    """
    headers = await get_auth_headers(async_client, "publish_valid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is True
    assert data["published"] is True
    assert data["version_number"] == 1
    assert data["version_id"] is not None
    assert data["published_at"] is not None

    # Flow should now be PUBLISHED
    flow_res = await async_client.get(f"/api/v1/automations/{flow_id}", headers=headers)
    flow = flow_res.json()["data"]
    assert flow["status"] == "published"
    assert flow["published_version_id"] is not None


@pytest.mark.asyncio
async def test_publish_increments_version_number(async_client: AsyncClient):
    """Publishing twice produces version 1 then version 2."""
    headers = await get_auth_headers(async_client, "publish_v2@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    res1 = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    assert res1.json()["data"]["version_number"] == 1

    # Save draft again and publish
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)
    res2 = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    assert res2.json()["data"]["version_number"] == 2


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_versions_list(async_client: AsyncClient):
    """GET /versions returns all versions, newest first, with is_active flag."""
    headers = await get_auth_headers(async_client, "versions_list@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    # Publish v1
    await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    # Publish v2
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)
    await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)

    res = await async_client.get(f"/api/v1/automations/{flow_id}/versions", headers=headers)
    assert res.status_code == 200
    versions = res.json()["data"]
    assert len(versions) == 2

    # Newest (v2) should be first and is_active
    assert versions[0]["version_number"] == 2
    assert versions[0]["is_active"] is True

    # v1 is not active
    assert versions[1]["version_number"] == 1
    assert versions[1]["is_active"] is False


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rollback_creates_new_version(async_client: AsyncClient):
    """
    Rollback to v1 creates v3 (new snapshot) with same definition as v1.
    flow.published_version_id points to v3.
    """
    headers = await get_auth_headers(async_client, "rollback@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    # Publish v1
    pub1 = await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)
    v1_id = pub1.json()["data"]["version_id"]

    # Publish v2
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)
    await async_client.post(f"/api/v1/automations/{flow_id}/publish", headers=headers)

    # Rollback to v1
    rb_res = await async_client.post(
        f"/api/v1/automations/{flow_id}/rollback/{v1_id}", headers=headers
    )
    assert rb_res.status_code == 200
    rb_data = rb_res.json()["data"]
    assert rb_data["new_version_number"] == 3
    assert rb_data["rolled_back_to"] == 1

    # Confirm versions list shows 3 items and v3 is active
    ver_res = await async_client.get(f"/api/v1/automations/{flow_id}/versions", headers=headers)
    versions = ver_res.json()["data"]
    assert len(versions) == 3
    assert versions[0]["is_active"] is True
    assert versions[0]["version_number"] == 3


# ---------------------------------------------------------------------------
# Simulate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulate_no_draft_returns_error(async_client: AsyncClient):
    """Simulate without a draft returns an error response."""
    headers = await get_auth_headers(async_client, "sim_nodraft@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/simulate", json={}, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_simulate_invalid_draft_returns_errors(async_client: AsyncClient):
    """Simulate with invalid draft returns validation errors, not steps."""
    headers = await get_auth_headers(async_client, "sim_invalid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, INVALID_BUILDER_GRAPH)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/simulate", json={}, headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is False
    assert len(data["errors"]) >= 1
    assert data["steps"] == []


@pytest.mark.asyncio
async def test_simulate_no_dispatch(async_client: AsyncClient):
    """
    Simulate with valid draft:
    - Returns steps array (≥1 step)
    - dispatch_blocked is True on result
    - No messages actually sent
    """
    headers = await get_auth_headers(async_client, "sim_valid@example.com")
    flow_id = await create_blank_flow(async_client, headers)
    await save_draft(async_client, headers, flow_id, VALID_BUILDER_GRAPH)

    res = await async_client.post(
        f"/api/v1/automations/{flow_id}/simulate",
        json={"mock_payload": {"content": "Hello!", "sender": "+1234567890"}},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is True
    assert len(data["steps"]) >= 1
    assert data["dispatch_blocked"] is True
    # All steps must have dispatch_blocked=True (no real messages)
    for step in data["steps"]:
        if "would_dispatch" in step:
            assert step["would_dispatch"] is False


@pytest.mark.asyncio
async def test_simulate_send_message_shows_content(async_client: AsyncClient):
    """Simulate SEND_MESSAGE step exposes would_send field."""
    headers = await get_auth_headers(async_client, "sim_send@example.com")
    flow_id = await create_blank_flow(async_client, headers)

    graph = {
        "nodes": [
            {
                "id": "trigger-1",
                "type": "triggerNode",
                "position": {"x": 250, "y": 50},
                "data": {"nodeType": "MESSAGE_INBOUND", "platform": "whatsapp", "config": {}},
            },
            {
                "id": "node-1",
                "type": "actionNode",
                "position": {"x": 250, "y": 220},
                "data": {"nodeType": "SEND_MESSAGE", "config": {"content": "Welcome to our service!"}},
            },
        ],
        "edges": [{"id": "e1", "source": "trigger-1", "target": "node-1"}],
    }
    await save_draft(async_client, headers, flow_id, graph)

    res = await async_client.post(f"/api/v1/automations/{flow_id}/simulate", json={}, headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is True
    send_step = next(s for s in data["steps"] if s["node_type"] == "SEND_MESSAGE")
    assert send_step["would_send"] == "Welcome to our service!"


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_flow_name(async_client: AsyncClient):
    """PATCH /automations/{id} updates the flow name."""
    headers = await get_auth_headers(async_client, "update_name@example.com")
    flow_id = await create_blank_flow(async_client, headers, "Original Name")

    res = await async_client.patch(
        f"/api/v1/automations/{flow_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_flow(async_client: AsyncClient):
    """DELETE /automations/{id} removes the flow."""
    headers = await get_auth_headers(async_client, "delete_flow@example.com")
    flow_id = await create_blank_flow(async_client, headers, "To Be Deleted")

    res = await async_client.delete(f"/api/v1/automations/{flow_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True

    # Flow should no longer be found
    get_res = await async_client.get(f"/api/v1/automations/{flow_id}", headers=headers)
    assert get_res.json()["success"] is False
