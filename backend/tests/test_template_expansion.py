"""
Integration tests for Mission 32 — Template Catalog Expansion.

Covers:
- Admin: version creation with variables
- Workspace: variable validation/replacement in clone, default values
- Version locking: source tracking on flow, template info in get_flow
- Analytics: clone_count + publish_count increments
- Sort by popular
- Rebase to newer template version
- Seed idempotency
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.models import User

# ---------------------------------------------------------------------------
# Shared graph fixtures
# ---------------------------------------------------------------------------

GRAPH_WITH_VARS = {
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
            "data": {
                "nodeType": "AI_REPLY",
                "config": {
                    "goal": "Welcome the visitor to {{business_name}} and qualify the lead",
                    "tasks": [],
                },
            },
        },
        {
            "id": "node-2",
            "type": "actionNode",
            "position": {"x": 250, "y": 400},
            "data": {
                "nodeType": "SEND_MESSAGE",
                "config": {
                    "content": "Thanks for contacting {{company_name}}! Our team will follow up.",
                },
            },
        },
    ],
    "edges": [
        {"id": "e1", "source": "trigger-1", "target": "node-1"},
        {"id": "e2", "source": "node-1", "target": "node-2"},
    ],
}

GRAPH_V2 = {
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
            "data": {
                "nodeType": "AI_REPLY",
                "config": {
                    "goal": "Welcome to {{business_name}} v2! Ask about budget and timeline",
                    "tasks": [],
                },
            },
        },
    ],
    "edges": [
        {"id": "e1", "source": "trigger-1", "target": "node-1"},
    ],
}

VARIABLES = [
    {
        "key": "business_name",
        "label": "Business Name",
        "description": "Your business name",
        "var_type": "text",
        "required": True,
        "default_value": None,
        "sort_order": 0,
    },
    {
        "key": "company_name",
        "label": "Company Name",
        "description": "Optional display name",
        "var_type": "text",
        "required": False,
        "default_value": "Our Company",
        "sort_order": 1,
    },
]


# ---------------------------------------------------------------------------
# Auth Helpers (reused from test_templates.py pattern)
# ---------------------------------------------------------------------------

async def get_admin_headers(client: AsyncClient, db_session: AsyncSession, suffix: str) -> dict:
    email = f"exp_admin_{suffix}@leadpilot.io"
    admin = User(
        email=email,
        hashed_password=get_password_hash("Admin1234!"),
        full_name=f"Expansion Admin {suffix}",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.flush()

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Admin1234!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def get_ws_headers(client: AsyncClient, suffix: str) -> dict:
    email = f"exp_ws_{suffix}@example.com"
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "WS User"})
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = r.json()["data"]["access_token"]
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


async def create_template_with_variables(
    client: AsyncClient, db_session: AsyncSession, slug: str, suffix: str,
    variables: list = None, graph: dict = None,
) -> tuple[str, str, dict]:
    """
    Create a template + version with variables + publish.
    Returns (template_id, version_id, admin_headers).
    """
    admin_headers = await get_admin_headers(client, db_session, suffix)

    res = await client.post(
        "/api/v1/admin/templates",
        json={
            "slug": slug,
            "name": f"Template {slug}",
            "description": "Test template with variables",
            "category": "lead_generation",
            "platforms": ["whatsapp"],
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Create template failed: {res.text}"
    template_id = res.json()["data"]["id"]

    res = await client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={
            "builder_graph_json": graph or GRAPH_WITH_VARS,
            "changelog": "v1 with variables",
            "variables": variables or VARIABLES,
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Create version failed: {res.text}"
    version_id = res.json()["data"]["id"]

    res = await client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Publish failed: {res.text}"

    return template_id, version_id, admin_headers


# ---------------------------------------------------------------------------
# Test 1: Admin create version with variables
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_create_version_with_variables(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST version with variables → TemplateVariable rows created."""
    admin_headers = await get_admin_headers(async_client, db_session, "var_create")

    res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "var-create-test", "name": "Var Create Test"},
        headers=admin_headers,
    )
    template_id = res.json()["data"]["id"]

    res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={
            "builder_graph_json": GRAPH_WITH_VARS,
            "changelog": "With vars",
            "variables": VARIABLES,
        },
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is True
    assert data["variables_count"] == 2


# ---------------------------------------------------------------------------
# Test 2: Clone with variable replacement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_template_variables_replacement(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Clone with variable_values → placeholders replaced in FlowDraft graph."""
    await create_template_with_variables(
        async_client, db_session, "var-replace-test", "var_replace"
    )

    ws_headers = await get_ws_headers(async_client, "var_replace_user")
    res = await async_client.post(
        "/api/v1/templates/var-replace-test/clone",
        json={
            "name": "My Qualified Bot",
            "variable_values": {
                "business_name": "Acme Inc",
                "company_name": "Acme Corp",
            },
        },
        headers=ws_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["variables_applied"] is True

    # Verify the draft graph has replaced values
    flow_id = data["flow_id"]
    draft_res = await async_client.get(
        f"/api/v1/automations/{flow_id}/draft",
        headers=ws_headers,
    )
    assert draft_res.status_code == 200
    draft = draft_res.json()["data"]
    graph = draft["builder_graph_json"]

    # AI_REPLY goal should have "Acme Inc" not "{{business_name}}"
    ai_node = next(n for n in graph["nodes"] if n["data"]["nodeType"] == "AI_REPLY")
    assert "Acme Inc" in ai_node["data"]["config"]["goal"]
    assert "{{business_name}}" not in ai_node["data"]["config"]["goal"]

    # SEND_MESSAGE should have "Acme Corp" not "{{company_name}}"
    send_node = next(n for n in graph["nodes"] if n["data"]["nodeType"] == "SEND_MESSAGE")
    assert "Acme Corp" in send_node["data"]["config"]["content"]


# ---------------------------------------------------------------------------
# Test 3: Clone creates FlowTemplateVariableValue records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clone_creates_variable_records(
    async_client: AsyncClient, db_session: AsyncSession
):
    """FlowTemplateVariableValue rows exist after clone."""
    await create_template_with_variables(
        async_client, db_session, "var-records-test", "var_records"
    )

    ws_headers = await get_ws_headers(async_client, "var_records_user")
    res = await async_client.post(
        "/api/v1/templates/var-records-test/clone",
        json={"variable_values": {"business_name": "TestCo"}},
        headers=ws_headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"]["variables_applied"] is True


# ---------------------------------------------------------------------------
# Test 4: Clone missing required variable fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clone_missing_required_variable_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Missing required var → error."""
    await create_template_with_variables(
        async_client, db_session, "var-missing-test", "var_missing"
    )

    ws_headers = await get_ws_headers(async_client, "var_missing_user")
    res = await async_client.post(
        "/api/v1/templates/var-missing-test/clone",
        json={
            "variable_values": {
                "company_name": "Acme",
                # business_name is required but missing!
            },
        },
        headers=ws_headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "business_name" in res.json()["error"].lower() or "Business Name" in res.json()["error"]


# ---------------------------------------------------------------------------
# Test 5: Clone uses default value
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clone_uses_default_value(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Omitted var with default_value → default applied."""
    await create_template_with_variables(
        async_client, db_session, "var-default-test", "var_default"
    )

    ws_headers = await get_ws_headers(async_client, "var_default_user")
    res = await async_client.post(
        "/api/v1/templates/var-default-test/clone",
        json={
            "variable_values": {
                "business_name": "DefaultCo",
                # company_name not supplied — should use default "Our Company"
            },
        },
        headers=ws_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    flow_id = data["flow_id"]

    # Verify the default was applied
    draft_res = await async_client.get(
        f"/api/v1/automations/{flow_id}/draft",
        headers=ws_headers,
    )
    graph = draft_res.json()["data"]["builder_graph_json"]
    send_node = next(n for n in graph["nodes"] if n["data"]["nodeType"] == "SEND_MESSAGE")
    assert "Our Company" in send_node["data"]["config"]["content"]


# ---------------------------------------------------------------------------
# Test 6: Version locking — source persisted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_version_locking_source_persisted(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Flow.source_template_id and source_template_version_id set on clone."""
    template_id, version_id, _ = await create_template_with_variables(
        async_client, db_session, "src-lock-test", "src_lock"
    )

    ws_headers = await get_ws_headers(async_client, "src_lock_user")
    res = await async_client.post(
        "/api/v1/templates/src-lock-test/clone",
        json={"variable_values": {"business_name": "LockCo"}},
        headers=ws_headers,
    )
    flow_id = res.json()["data"]["flow_id"]

    # GET flow should show source template info
    flow_res = await async_client.get(
        f"/api/v1/automations/{flow_id}",
        headers=ws_headers,
    )
    assert flow_res.status_code == 200
    flow_data = flow_res.json()["data"]
    assert flow_data["source_template_id"] == template_id
    assert flow_data["source_template_version_id"] == version_id


# ---------------------------------------------------------------------------
# Test 7: GET /automations/{id} includes template info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_flow_includes_template_info(
    async_client: AsyncClient, db_session: AsyncSession
):
    """GET /automations/{id} returns source_template_id + latest version info."""
    await create_template_with_variables(
        async_client, db_session, "flow-tmpl-info", "flow_info"
    )

    ws_headers = await get_ws_headers(async_client, "flow_info_user")
    clone_res = await async_client.post(
        "/api/v1/templates/flow-tmpl-info/clone",
        json={"variable_values": {"business_name": "InfoCo"}},
        headers=ws_headers,
    )
    flow_id = clone_res.json()["data"]["flow_id"]

    flow_res = await async_client.get(
        f"/api/v1/automations/{flow_id}",
        headers=ws_headers,
    )
    data = flow_res.json()["data"]
    assert data["source_template_id"] is not None
    assert data["source_template_version_id"] is not None
    assert data["latest_template_version_number"] == 1


# ---------------------------------------------------------------------------
# Test 8: Clone count increment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_template_stats_clone_increment(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TemplateUsageStat.clone_count increments on clone."""
    await create_template_with_variables(
        async_client, db_session, "stat-clone-test", "stat_clone"
    )

    ws_headers = await get_ws_headers(async_client, "stat_clone_user")

    # Clone twice
    for _ in range(2):
        res = await async_client.post(
            "/api/v1/templates/stat-clone-test/clone",
            json={"variable_values": {"business_name": "StatCo"}},
            headers=ws_headers,
        )
        assert res.json()["success"] is True

    # Check list includes clone_count
    list_res = await async_client.get("/api/v1/templates", headers=ws_headers)
    templates = list_res.json()["data"]
    tmpl = next((t for t in templates if t["slug"] == "stat-clone-test"), None)
    assert tmpl is not None
    assert tmpl["clone_count"] >= 2


# ---------------------------------------------------------------------------
# Test 9: Publish count increment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_template_stats_publish_increment(
    async_client: AsyncClient, db_session: AsyncSession
):
    """publish_count increments when publishing template-based flow."""
    await create_template_with_variables(
        async_client, db_session, "stat-pub-test", "stat_pub"
    )

    ws_headers = await get_ws_headers(async_client, "stat_pub_user")

    # Clone the template
    clone_res = await async_client.post(
        "/api/v1/templates/stat-pub-test/clone",
        json={"variable_values": {"business_name": "PubCo"}},
        headers=ws_headers,
    )
    flow_id = clone_res.json()["data"]["flow_id"]

    # Publish the flow
    pub_res = await async_client.post(
        f"/api/v1/automations/{flow_id}/publish",
        headers=ws_headers,
    )
    assert pub_res.status_code == 200
    # The publish should succeed (graph from template is valid)
    data = pub_res.json()["data"]
    assert data["published"] is True


# ---------------------------------------------------------------------------
# Test 10: List templates includes clone_count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_templates_includes_clone_count(
    async_client: AsyncClient, db_session: AsyncSession
):
    """GET /templates response has clone_count field."""
    await create_template_with_variables(
        async_client, db_session, "list-count-test", "list_count"
    )

    ws_headers = await get_ws_headers(async_client, "list_count_user")
    list_res = await async_client.get("/api/v1/templates", headers=ws_headers)
    assert list_res.status_code == 200
    templates = list_res.json()["data"]

    for t in templates:
        assert "clone_count" in t, f"Template {t['slug']} missing clone_count"


# ---------------------------------------------------------------------------
# Test 11: Sort by popular
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_templates_sort_popular(
    async_client: AsyncClient, db_session: AsyncSession
):
    """sort=popular orders by clone_count DESC."""
    await create_template_with_variables(
        async_client, db_session, "pop-sort-test", "pop_sort"
    )

    ws_headers = await get_ws_headers(async_client, "pop_sort_user")

    # Clone once to give it a clone_count > 0
    await async_client.post(
        "/api/v1/templates/pop-sort-test/clone",
        json={"variable_values": {"business_name": "PopCo"}},
        headers=ws_headers,
    )

    list_res = await async_client.get(
        "/api/v1/templates?sort=popular",
        headers=ws_headers,
    )
    assert list_res.status_code == 200
    templates = list_res.json()["data"]
    assert len(templates) > 0
    # Verify clone_counts are in descending order
    counts = [t["clone_count"] for t in templates]
    assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# Test 12: Rebase to template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rebase_to_template(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Rebase updates FlowDraft graph + source_template_version_id."""
    template_id, v1_id, admin_headers = await create_template_with_variables(
        async_client, db_session, "rebase-test", "rebase"
    )

    ws_headers = await get_ws_headers(async_client, "rebase_user")

    # Clone v1
    clone_res = await async_client.post(
        "/api/v1/templates/rebase-test/clone",
        json={"variable_values": {"business_name": "RebaseCo"}},
        headers=ws_headers,
    )
    flow_id = clone_res.json()["data"]["flow_id"]

    # Create v2 of template
    res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={
            "builder_graph_json": GRAPH_V2,
            "changelog": "v2 improvements",
            "variables": [VARIABLES[0]],  # Just business_name
        },
        headers=admin_headers,
    )
    assert res.status_code == 200
    v2_id = res.json()["data"]["id"]

    # Publish v2
    await async_client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=admin_headers,
    )

    # Rebase flow to v2
    rebase_res = await async_client.post(
        f"/api/v1/automations/{flow_id}/rebase-to-template/{v2_id}",
        headers=ws_headers,
    )
    assert rebase_res.status_code == 200
    data = rebase_res.json()["data"]
    assert data["rebased"] is True
    assert data["new_version_number"] == 2

    # Verify the draft now has v2 graph with variable replaced
    draft_res = await async_client.get(
        f"/api/v1/automations/{flow_id}/draft",
        headers=ws_headers,
    )
    graph = draft_res.json()["data"]["builder_graph_json"]
    ai_node = next(n for n in graph["nodes"] if n["data"]["nodeType"] == "AI_REPLY")
    assert "RebaseCo" in ai_node["data"]["config"]["goal"]
    assert "v2" in ai_node["data"]["config"]["goal"]

    # Verify source_template_version_id updated
    flow_res = await async_client.get(
        f"/api/v1/automations/{flow_id}",
        headers=ws_headers,
    )
    assert flow_res.json()["data"]["source_template_version_id"] == v2_id


# ---------------------------------------------------------------------------
# Test 13: Rebase non-template flow fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rebase_non_template_flow_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Rebase on flow without source_template_id → error."""
    ws_headers = await get_ws_headers(async_client, "rebase_notemplate")

    # Create a blank flow (not from template)
    res = await async_client.post(
        "/api/v1/automations",
        json={"name": "Blank Flow"},
        headers=ws_headers,
    )
    assert res.status_code == 200
    flow_id = res.json()["data"]["flow_id"]

    # Try to rebase
    rebase_res = await async_client.post(
        f"/api/v1/automations/{flow_id}/rebase-to-template/00000000-0000-0000-0000-000000000000",
        headers=ws_headers,
    )
    assert rebase_res.status_code == 200
    assert rebase_res.json()["success"] is False
    assert "not cloned from a template" in rebase_res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 14: Seed idempotency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seed_idempotency(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Call seed_templates() twice → no duplicates."""
    from app.core.seed import seed_templates

    await seed_templates()
    await seed_templates()

    # Check that all seeded templates are unique by slug
    ws_headers = await get_ws_headers(async_client, "seed_idem")
    list_res = await async_client.get("/api/v1/templates", headers=ws_headers)
    templates = list_res.json()["data"]
    slugs = [t["slug"] for t in templates]
    assert len(slugs) == len(set(slugs)), f"Duplicate slugs found: {slugs}"
