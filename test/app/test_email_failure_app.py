"""
Tests for src/app.py related to email failure scenarios.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from src.app import app as flask_app

@pytest.fixture
def client_with_email_failure_fixture(monkeypatch):
    """
    Fixture that configures the Flask client with test email environment.
    """
    flask_app.config.update({"TESTING": True})
    monkeypatch.setenv("API_KEY", "test-api-key-123")
    return flask_app.test_client()

@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_email_failure(mock_execute, client_with_email_failure_fixture):
    """
    Test email sending in case of endpoint execution failure.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    with patch("email_service.EmailNotificationService.send_notification") as mock_send_email:
        mock_send_email.return_value = {
            "email_sent": True,
            "recipient": "recipient@example.com",
            "from": "test@gmail.com",
            "attachments": 1,
        }
        response = client_with_email_failure_fixture.post(
            "/execute",
            data=json.dumps(
                {
                    "endpoints": ["https://api.example.com/test"],
                    "send_email": True,
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "test-api-key-123"},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["email_notification"]["email_sent"] is True
        assert data["email_notification"]["attachments"] == 1
