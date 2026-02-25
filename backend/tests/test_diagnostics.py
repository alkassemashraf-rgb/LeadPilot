import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_diagnostics_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/diagnostics")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    
    payload = data["data"]
    assert "db_ok" in payload
    assert "redis_ok" in payload
    assert "worker_queue_ok" in payload
    assert "llm_ok" in payload
    assert "correlation_id" in payload
    
    # DB Should be OK in test environment
    assert payload["db_ok"] is True
