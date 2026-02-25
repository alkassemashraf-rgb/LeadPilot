import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from unittest.mock import patch
from app.models.models import User

@pytest.mark.asyncio
async def test_signup(async_client: AsyncClient, db_session: AsyncSession):
    payload = {
        "email": "test_signup@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    response = await async_client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == payload["email"]
    assert "id" in data["data"]
    
    # Verify in DB
    result = await db_session.execute(select(User).where(User.email == payload["email"]))
    user = result.scalars().first()
    assert user is not None

@pytest.mark.asyncio
async def test_login(async_client: AsyncClient):
    # Setup: Create user first
    signup_payload = {
        "email": "test_login@example.com",
        "password": "securepassword123",
        "full_name": "Login User"
    }
    await async_client.post("/api/v1/auth/signup", json=signup_payload)
    
    # Test Login
    login_payload = {
        "username": "test_login@example.com",
        "password": "securepassword123"
    }
    response = await async_client.post(
        "/api/v1/auth/login", 
        data=login_payload, 
        headers={"content-type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_forgot_password(async_client: AsyncClient):
    payload = {"email": "nonexistent@example.com"}
    response = await async_client.post("/api/v1/auth/forgot-password", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Should perform generic success validation
    assert "message" in data["data"]

@pytest.mark.asyncio
@patch("app.api.v1.auth.send_email_task.delay")
async def test_forgot_password_email_flow(mock_send_email_task_delay, async_client: AsyncClient, db_session: AsyncSession):
    # Setup: Create user first
    signup_payload = {
        "email": "test_forgot_flow@example.com",
        "password": "securepassword123",
        "full_name": "Forgot Flow User"
    }
    await async_client.post("/api/v1/auth/signup", json=signup_payload)
    
    # Test Forgot Password
    forgot_payload = {"email": "test_forgot_flow@example.com"}
    
    response = await async_client.post("/api/v1/auth/forgot-password", json=forgot_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify mock was called
    mock_send_email_task_delay.assert_called_once()
    args, kwargs = mock_send_email_task_delay.call_args
    assert args[0] == "password_reset"
    assert "token" in args[1]
    assert args[1]["to_email"] == "test_forgot_flow@example.com"
