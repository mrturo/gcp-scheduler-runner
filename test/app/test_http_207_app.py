"""
Tests for src/app.py related to HTTP 207 Multi-Status handling.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

from test.helpers import assert_execute_response

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
    payload = {"endpoints": ["https://external-api.example.com/batch-task"]}
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 207
    data = json.loads(response.data)
    assert_execute_response(data, False, 1, 0, 0)
    assert len(data["details"]["warnings"]) == 1
    assert data["details"]["warnings"][0]["status_code"] == 207

@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoint_returns_200_when_all_success(mock_execute, client):
    """
    Test /execute returns 200 when all tasks succeed.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": [
            "https://api.example.com/task1",
            "https://api.example.com/task2",
        ]
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_execute_response(data, True, 0, 2, 0)
