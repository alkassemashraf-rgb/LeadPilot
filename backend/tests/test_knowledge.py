"""Tests for Knowledge Files API — Mission 20."""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def get_auth_headers(client: AsyncClient, email: str = "kb@test.com") -> dict:
    pwd = "password123"
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd, "full_name": "KB Tester"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": pwd},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_res.json()["data"]["access_token"]
    ws_res = await client.get(
        "/api/v1/workspaces", headers={"Authorization": f"Bearer {token}"}
    )
    ws_id = ws_res.json()["data"][0]["id"]
    return {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_id}


@pytest.mark.asyncio
async def test_upload_and_list_knowledge_file(async_client: AsyncClient):
    """Upload a .txt file and verify it appears in the list."""
    headers = await get_auth_headers(async_client, "kb_upload@test.com")

    file_content = b"Our pricing starts at $99/month for the basic plan."
    res = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("pricing.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["extracted"] is True
    assert body["data"]["status"] == "READY"

    # List files
    list_res = await async_client.get("/api/v1/knowledge/files", headers=headers)
    assert list_res.status_code == 200
    files = list_res.json()["data"]
    assert len(files) >= 1
    found = [f for f in files if f["filename"] == "pricing.txt"]
    assert len(found) == 1
    assert found[0]["status"] == "READY"
    assert found[0]["extracted"] is True


@pytest.mark.asyncio
async def test_sha256_dedupe_rejects_duplicate(async_client: AsyncClient):
    """Uploading the same content twice should return an error."""
    headers = await get_auth_headers(async_client, "kb_dedupe@test.com")

    file_content = b"Unique content for dedup test 12345"
    # First upload
    res1 = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("doc1.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res1.json()["success"] is True

    # Second upload — same content, different filename
    res2 = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("doc2.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    assert res2.status_code == 200
    body = res2.json()
    assert body["success"] is False
    assert "Duplicate" in body["error"]


@pytest.mark.asyncio
async def test_delete_knowledge_file(async_client: AsyncClient):
    """Upload then delete a file and confirm it's gone."""
    headers = await get_auth_headers(async_client, "kb_delete@test.com")

    file_content = b"File to be deleted"
    upload_res = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("deleteme.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    file_id = upload_res.json()["data"]["id"]

    # Delete
    del_res = await async_client.delete(
        f"/api/v1/knowledge/files/{file_id}", headers=headers
    )
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # Verify gone from list
    list_res = await async_client.get("/api/v1/knowledge/files", headers=headers)
    ids = [f["id"] for f in list_res.json()["data"]]
    assert file_id not in ids


@pytest.mark.asyncio
async def test_download_knowledge_file(async_client: AsyncClient):
    """Upload a file and download it back."""
    headers = await get_auth_headers(async_client, "kb_download@test.com")

    file_content = b"Download me!"
    upload_res = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("download.txt", io.BytesIO(file_content), "text/plain")},
        headers=headers,
    )
    file_id = upload_res.json()["data"]["id"]

    # Download
    dl_res = await async_client.get(
        f"/api/v1/knowledge/files/{file_id}/download", headers=headers
    )
    assert dl_res.status_code == 200
    assert dl_res.content == file_content


@pytest.mark.asyncio
async def test_upload_unsupported_format_status(async_client: AsyncClient):
    """Upload a .bin file — should have status READY but no extracted text."""
    headers = await get_auth_headers(async_client, "kb_bin@test.com")

    res = await async_client.post(
        "/api/v1/knowledge/files",
        files={"file": ("data.bin", io.BytesIO(b"\x00\x01\x02"), "application/octet-stream")},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    # Unsupported format → no extraction, but still READY
    assert body["data"]["extracted"] is False
