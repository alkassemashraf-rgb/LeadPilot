"""
Integration tests for the Template Catalog (Mission 27).

Covers:
- Admin: create/patch/list templates and versions, publish
- Workspace: list, get, clone templates
- Edge cases: duplicate slug, invalid graph, no published version
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.models import User

# ---------------------------------------------------------------------------
# Shared graph fixture
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
            "data": {
                "nodeType": "AI_REPLY",
                "config": {"goal": "Welcome and qualify the lead", "tasks": []},
            },
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
            "data": {"nodeType": "AI_REPLY", "config": {"goal": ""}},  # missing goal → invalid
        },
    ],
    "edges": [{"id": "e1", "source": "trigger-1", "target": "node-1"}],
}

# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------

async def get_admin_headers(client: AsyncClient, db_session: AsyncSession, suffix: str) -> dict:
    """Create a superadmin user directly in DB and return auth headers."""
    email = f"tmpl_admin_{suffix}@leadpilot.io"
    admin = User(
        email=email,
        hashed_password=get_password_hash("Admin1234!"),
        full_name=f"Template Admin {suffix}",
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
    """Create a regular workspace user and return auth + workspace headers."""
    email = f"tmpl_ws_{suffix}@example.com"
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd, "full_name": "WS User"})
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    token = r.json()["data"]["access_token"]
    ws_res = await client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"})
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


async def create_published_template(
    client: AsyncClient, db_session: AsyncSession, slug: str, suffix: str
) -> tuple[str, dict]:
    """
    Helper: create a template + published version via admin endpoints.
    Returns (template_id, admin_headers).
    """
    admin_headers = await get_admin_headers(client, db_session, suffix)

    # Create template
    res = await client.post(
        "/api/v1/admin/templates",
        json={
            "slug": slug,
            "name": f"Template {slug}",
            "description": "Test template",
            "category": "lead_generation",
            "platforms": ["whatsapp"],
        },
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Create template failed: {res.text}"
    template_id = res.json()["data"]["id"]

    # Create version
    res = await client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": VALID_BUILDER_GRAPH, "changelog": "Initial version"},
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Create version failed: {res.text}"

    # Publish version
    res = await client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=admin_headers,
    )
    assert res.status_code == 200, f"Publish failed: {res.text}"

    return template_id, admin_headers


# ---------------------------------------------------------------------------
# Admin — Template CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_create_template(async_client: AsyncClient, db_session: AsyncSession):
    """Admin can create a new template. Returns id + slug."""
    headers = await get_admin_headers(async_client, db_session, "create")

    res = await async_client.post(
        "/api/v1/admin/templates",
        json={
            "slug": "welcome-bot",
            "name": "Welcome Bot",
            "description": "Greet new leads automatically.",
            "category": "lead_generation",
            "platforms": ["whatsapp"],
            "is_featured": True,
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["slug"] == "welcome-bot"
    assert "id" in data


@pytest.mark.asyncio
async def test_admin_create_template_duplicate_slug_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Creating two templates with the same slug returns an error."""
    headers = await get_admin_headers(async_client, db_session, "dup")

    payload = {"slug": "dup-slug", "name": "First"}
    await async_client.post("/api/v1/admin/templates", json=payload, headers=headers)

    res = await async_client.post("/api/v1/admin/templates", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "already exists" in res.json()["error"]


@pytest.mark.asyncio
async def test_admin_patch_template(async_client: AsyncClient, db_session: AsyncSession):
    """Admin can patch template name and featured flag."""
    headers = await get_admin_headers(async_client, db_session, "patch")

    create_res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "patch-test", "name": "Original Name"},
        headers=headers,
    )
    template_id = create_res.json()["data"]["id"]

    res = await async_client.patch(
        f"/api/v1/admin/templates/{template_id}",
        json={"name": "Updated Name", "is_featured": True},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["updated"] is True


@pytest.mark.asyncio
async def test_admin_list_templates_includes_inactive(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Admin template list includes both active and inactive templates."""
    headers = await get_admin_headers(async_client, db_session, "listall")

    # Create one and deactivate
    res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "inactive-one", "name": "Inactive"},
        headers=headers,
    )
    template_id = res.json()["data"]["id"]
    await async_client.patch(
        f"/api/v1/admin/templates/{template_id}",
        json={"is_active": False},
        headers=headers,
    )

    list_res = await async_client.get("/api/v1/admin/templates", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    # The deactivated template should be in the list
    found = any(i["slug"] == "inactive-one" for i in items)
    assert found, "Admin list should include inactive templates"


# ---------------------------------------------------------------------------
# Admin — Template Versions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_create_template_version(async_client: AsyncClient, db_session: AsyncSession):
    """Admin can create a new draft version. Returns version_id + version_number."""
    headers = await get_admin_headers(async_client, db_session, "ver_create")

    create_res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "ver-create-test", "name": "Version Create Test"},
        headers=headers,
    )
    template_id = create_res.json()["data"]["id"]

    res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": VALID_BUILDER_GRAPH, "changelog": "v1 initial"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is True
    assert data["version_number"] == 1
    assert "id" in data


@pytest.mark.asyncio
async def test_admin_create_version_invalid_graph_returns_errors(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Creating a version with an invalid graph returns validation errors, not 500."""
    headers = await get_admin_headers(async_client, db_session, "ver_invalid")

    create_res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "ver-invalid-test", "name": "Invalid Version Test"},
        headers=headers,
    )
    template_id = create_res.json()["data"]["id"]

    res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": INVALID_BUILDER_GRAPH},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid"] is False
    assert len(data["errors"]) >= 1


@pytest.mark.asyncio
async def test_admin_publish_template_version(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    After creating a version, publish marks it is_published=True.
    Response includes version_number + published_at.
    """
    headers = await get_admin_headers(async_client, db_session, "pub_ver")

    res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "pub-ver-test", "name": "Pub Ver Test"},
        headers=headers,
    )
    template_id = res.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": VALID_BUILDER_GRAPH},
        headers=headers,
    )

    pub_res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=headers,
    )
    assert pub_res.status_code == 200
    data = pub_res.json()["data"]
    assert data["published"] is True
    assert data["version_number"] == 1
    assert data["published_at"] is not None


@pytest.mark.asyncio
async def test_admin_publish_no_unpublished_version_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Publishing when all versions are already published returns an error."""
    template_id, headers = await create_published_template(
        async_client, db_session, "already-pub", "alreadypub"
    )

    # Try to publish again — no more unpublished versions
    res = await async_client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is False


@pytest.mark.asyncio
async def test_admin_list_template_versions(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Admin can list all versions for a template."""
    headers = await get_admin_headers(async_client, db_session, "list_ver")

    res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "list-ver-test", "name": "List Ver Test"},
        headers=headers,
    )
    template_id = res.json()["data"]["id"]

    # Create two versions
    await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": VALID_BUILDER_GRAPH, "changelog": "v1"},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/admin/templates/{template_id}/publish",
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/admin/templates/{template_id}/versions",
        json={"builder_graph_json": VALID_BUILDER_GRAPH, "changelog": "v2"},
        headers=headers,
    )

    ver_res = await async_client.get(
        f"/api/v1/admin/templates/{template_id}/versions",
        headers=headers,
    )
    assert ver_res.status_code == 200
    versions = ver_res.json()["data"]
    assert len(versions) == 2
    # Newest first
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1
    assert versions[1]["is_published"] is True


# ---------------------------------------------------------------------------
# Workspace — Template Catalog Browsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_list_templates(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Workspace users only see active templates with published versions."""
    # Create and publish a template via admin
    await create_published_template(async_client, db_session, "ws-list-t1", "wslist1")

    # Create an inactive template
    admin_headers = await get_admin_headers(async_client, db_session, "wslist_inactive")
    res = await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "ws-inactive-t", "name": "Inactive Template"},
        headers=admin_headers,
    )
    template_id = res.json()["data"]["id"]
    await async_client.patch(
        f"/api/v1/admin/templates/{template_id}",
        json={"is_active": False},
        headers=admin_headers,
    )

    ws_headers = await get_ws_headers(async_client, "wslist")
    list_res = await async_client.get("/api/v1/templates", headers=ws_headers)
    assert list_res.status_code == 200
    templates = list_res.json()["data"]

    # All returned templates must be active
    for t in templates:
        assert t["slug"] != "ws-inactive-t", "Inactive template should not appear"


@pytest.mark.asyncio
async def test_workspace_get_template_detail(
    async_client: AsyncClient, db_session: AsyncSession
):
    """GET /templates/{slug} returns full detail including latest_version."""
    await create_published_template(async_client, db_session, "ws-detail-t", "wsdetail")

    ws_headers = await get_ws_headers(async_client, "wsdetail_user")
    res = await async_client.get("/api/v1/templates/ws-detail-t", headers=ws_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["slug"] == "ws-detail-t"
    assert data["latest_version"] is not None
    assert data["latest_version"]["builder_graph_json"] is not None
    assert data["latest_version"]["version_number"] == 1


@pytest.mark.asyncio
async def test_workspace_get_template_not_found(async_client: AsyncClient, db_session: AsyncSession):
    """GET /templates/{slug} for non-existent slug returns error."""
    ws_headers = await get_ws_headers(async_client, "wsnotfound")
    res = await async_client.get("/api/v1/templates/does-not-exist", headers=ws_headers)
    assert res.status_code == 200
    assert res.json()["success"] is False


# ---------------------------------------------------------------------------
# Workspace — Clone Template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_clone_template(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    POST /templates/{slug}/clone:
    - Creates a Flow (DRAFT) in the workspace
    - Creates a FlowDraft with builder_graph_json from the template version
    - Returns flow_id + redirect_path
    """
    await create_published_template(async_client, db_session, "ws-clone-t", "wsclone")

    ws_headers = await get_ws_headers(async_client, "wsclone_user")
    res = await async_client.post(
        "/api/v1/templates/ws-clone-t/clone",
        json={"name": "My Cloned Flow"},
        headers=ws_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "flow_id" in data
    assert data["redirect_path"] == f"/automations/{data['flow_id']}"
    assert data["template_slug"] == "ws-clone-t"

    # Verify draft was created with the template graph
    flow_id = data["flow_id"]
    draft_res = await async_client.get(
        f"/api/v1/automations/{flow_id}/draft",
        headers=ws_headers,
    )
    assert draft_res.status_code == 200
    draft = draft_res.json()["data"]
    assert draft["builder_graph_json"] is not None
    assert len(draft["builder_graph_json"]["nodes"]) == 2  # trigger + AI_REPLY


@pytest.mark.asyncio
async def test_workspace_clone_template_default_name(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Clone without a name defaults to the template name."""
    await create_published_template(async_client, db_session, "ws-noname-t", "wsnoname")

    ws_headers = await get_ws_headers(async_client, "wsnoname_user")
    res = await async_client.post(
        "/api/v1/templates/ws-noname-t/clone",
        json={},  # no name provided
        headers=ws_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["flow_name"] == "Template ws-noname-t"


@pytest.mark.asyncio
async def test_workspace_clone_no_published_version_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Clone a template that exists but has no published version returns an error."""
    admin_headers = await get_admin_headers(async_client, db_session, "nopubver")

    # Create template WITHOUT publishing a version
    await async_client.post(
        "/api/v1/admin/templates",
        json={"slug": "no-pub-version", "name": "No Published Version"},
        headers=admin_headers,
    )

    ws_headers = await get_ws_headers(async_client, "nopub_user")
    res = await async_client.post(
        "/api/v1/templates/no-pub-version/clone",
        json={},
        headers=ws_headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
    assert "no published version" in res.json()["error"].lower()


@pytest.mark.asyncio
async def test_workspace_clone_nonexistent_template_fails(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Clone a template that doesn't exist returns an error."""
    ws_headers = await get_ws_headers(async_client, "clone_missing")
    res = await async_client.post(
        "/api/v1/templates/absolutely-does-not-exist/clone",
        json={},
        headers=ws_headers,
    )
    assert res.status_code == 200
    assert res.json()["success"] is False
