import pytest
from unittest.mock import patch, MagicMock
from app.services.email_providers.sendgrid_provider import SendGridProvider, EmailTransportError
from app.api.v1.diagnostics import get_diagnostics
from app.core.config import settings
import httpx
from httpx import Response
from app.services.email_service import EmailService
from starlette.requests import Request

@pytest.fixture
def sendgrid_provider():
    return SendGridProvider()

@pytest.mark.asyncio
async def test_sendgrid_provider_success_202(sendgrid_provider, monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "test@test.com")
    
    class MockAsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, headers=None, json=None):
            return Response(status_code=202)

    with patch("httpx.AsyncClient", return_value=MockAsyncClient()):
        result = await sendgrid_provider.send_email(
            to_email="user@test.com",
            subject="Test",
            html_content="<p>Test</p>",
            message_id="idemp-key",
            email_log_id="log-id"
        )
        assert result is True

@pytest.mark.asyncio
async def test_sendgrid_provider_failure_non_202(sendgrid_provider, monkeypatch):
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "test@test.com")
    
    class MockAsyncClientFail:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def post(self, url, headers=None, json=None):
            return Response(status_code=400, text="Bad Request")

    with patch("httpx.AsyncClient", return_value=MockAsyncClientFail()):
        with pytest.raises(EmailTransportError) as exc_info:
            await sendgrid_provider.send_email(
                to_email="user@test.com",
                subject="Test",
                html_content="<p>Test</p>"
            )
        assert "SendGrid API Error 400" in str(exc_info.value)

@pytest.mark.asyncio
async def test_outbox_routes_to_sendgrid(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "sendgrid")
    
    with patch("app.services.email_providers.sendgrid_provider.SendGridProvider.send_email") as mock_send:
        mock_send.return_value = True
        
        # Calling the factory method
        result = await EmailService.send_email(
            to_email="user@test.com",
            subject="Test Route",
            html_content="<p>test</p>"
        )
        
        assert result is True
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_diagnostics_reports_sendgrid(monkeypatch, db_session):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "test@test.com")
    
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    mock_request.state.correlation_id = "test-corr-id"
    
    diag_resp = await get_diagnostics(request=mock_request, db=db_session)
    data = diag_resp.data
    
    assert data["email_provider"] == "sendgrid"
    assert data["sendgrid_configured"] is True

@pytest.mark.asyncio
async def test_diagnostics_reports_sendgrid_not_configured(monkeypatch, db_session):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "sendgrid")
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "")
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "test@test.com")
    
    mock_request = MagicMock(spec=Request)
    mock_request.state = MagicMock()
    mock_request.state.correlation_id = "test-corr-id"
    
    diag_resp = await get_diagnostics(request=mock_request, db=db_session)
    data = diag_resp.data
    
    assert data["email_provider"] == "sendgrid"
    assert data["sendgrid_configured"] is False
