
"""
Tests for src/app.py related to email notification integration.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from src.app import app as flask_app
from test.helpers import assert_email_notification_success


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_send_email_success(mock_execute, client):
    """
    Test successful email sending when send_email=True.
    """
    with patch("app.EmailNotificationService.send_notification") as mock_send_email, patch(
        "app.EmailConfig"
    ) as mock_email_config_class:
        mock_email_config_instance = MagicMock()
        mock_email_config_class.return_value = mock_email_config_instance
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_execute.return_value = mock_response
        mock_send_email.return_value = {
            "email_sent": True,
            "recipient": "recipient@example.com",
            "from": "sender@example.com",
            "attachments": 1,
        }
        response = client.post(
            "/execute",
            data=json.dumps(
                {
                    "endpoints": ["https://api.example.com/test"],
                    "send_email": True,
                    "test_mode": True,
                }
            ),
            content_type="application/json",
            headers={"X-API-Key": "test-api-key-123"},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert_email_notification_success(data, "recipient@example.com", "sender@example.com", 1)


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_send_email_false(mock_execute, client):
    """
    Test that no email is sent when send_email=False.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    response = client.post(
        "/execute",
        data=json.dumps(
            {
                "endpoints": ["https://api.example.com/test"],
                "send_email": False,
                "test_mode": True,
            }
        ),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "email_notification" in data
    assert data["email_notification"]["email_sent"] is False
    assert data["email_notification"]["reason"] == "Email notification was not requested"


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_default_no_email(mock_execute, client):
    """
    Test that no email is sent if send_email is not present in the request.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    response = client.post(
        "/execute",
        data=json.dumps({"endpoints": ["https://api.example.com/test"], "test_mode": True}),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "email_notification" in data
    assert data["email_notification"]["email_sent"] is False
    assert data["email_notification"]["reason"] == "Email notification was not requested"
