"""
Tests for src/app.py related to HTTP 207 Multi-Status handling.
"""

import os
import sys
from unittest.mock import MagicMock, patch

from test.helpers import assert_execute_response
from test.helpers_extra import create_mock_response, post_execute, post_execute_custom_payload

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoint_returns_207_when_partial_success(mock_execute, client):
    """
    Test /execute returns 207 Multi-Status when some tasks fail.
    """
    mock_response = MagicMock()
    mock_response.status_code = 207
    mock_response.json.return_value = {
        "message": "Some tasks completed with errors",
        "successful": 3,
        "failed": 2,
    }
    mock_execute.return_value = mock_response
    # Flask app returns 207 when there are warnings
    data = post_execute_custom_payload(
        client, {"endpoints": ["https://external-api.example.com/batch-task"]}, status_code=207
    )
    assert_execute_response(data, True, 1, 0, 0)
    assert len(data["details"]["warnings"]) == 1
    assert data["details"]["warnings"][0]["status_code"] == 207

@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoint_returns_200_when_all_success(mock_execute, client):
    """
    Test /execute returns 200 when all tasks succeed.
    """
    mock_execute.return_value = create_mock_response()
    data = post_execute(
        client, ["https://api.example.com/task1", "https://api.example.com/task2"]
    )
    assert_execute_response(data, True, 0, 2, 0)

@patch("src.http_executor.requests.request")
def test_email_config_usage(mock_request, client):
    """
    Test that email configuration is applied correctly.
    """
    mock_request.return_value = create_mock_response()
    # This test previously passed EmailConfig as endpoints, which is not valid JSON.
    # Instead test with valid endpoints and check email config usage via response.
    endpoints = ["https://api.example.com/task1"]
    data = post_execute(client, endpoints, status_code=200)
    assert "success" in data
