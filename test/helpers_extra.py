"""
Helper functions for testing.
"""

import json
from unittest.mock import MagicMock

from src.models import EmailConfig as EmailConfigModel


def make_email_config():
    """Helper to create a standard EmailConfigModel for tests."""
    return EmailConfigModel(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="password",
        email_from="test@example.com",
        email_to="recipient@example.com",
    )


def create_mock_response(status_code=200, json_data=None):
    """Helper to create a standard mock response for tests."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_data is None:
        json_data = {"result": "success"}
    mock_response.json.return_value = json_data
    mock_response.text = json.dumps(json_data)
    return mock_response


def post_execute(client, endpoints, status_code=200, parallel=True, requests_mock=None):
    """Helper to post to /execute with standard payload. Optionally mocks requests.request."""
    payload = {"endpoints": endpoints, "parallel": parallel}
    if requests_mock is not None:
        with requests_mock:
            response = client.post(
                "/execute",
                data=json.dumps(payload),
                content_type="application/json",
                headers={"X-API-Key": "test-api-key-123"},
            )
    else:
        response = client.post(
            "/execute",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-API-Key": "test-api-key-123"},
        )
    assert response.status_code == status_code
    return json.loads(response.data)


def post_execute_custom_payload(client, payload, status_code=200):
    """Helper to post to /execute with custom payload."""
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == status_code
    return json.loads(response.data)
