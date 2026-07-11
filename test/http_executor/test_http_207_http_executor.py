"""
Tests for src/http_executor.py related to HTTP 207 Multi-Status and error handling.
"""

import os
import sys
from unittest.mock import MagicMock, patch
from test.helpers_extra import post_execute

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@patch("src.http_executor.time.sleep")
@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_mixed_success_warning_error(mock_execute, _mock_sleep, client):
    """
    Test /execute with mixed 200, 207, and 500 responses.
    The 500 endpoint is retried up to max_attempts; sleep is mocked for test speed.
    """
    call_count = [0]

    def side_effect_function(*_args, **_kwargs):
        call_count[0] += 1
        mock_response = MagicMock()
        if call_count[0] == 1:
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "ok"}
        elif call_count[0] == 2:
            mock_response.status_code = 207
            mock_response.json.return_value = {"partial": "success"}
        else:
            mock_response.status_code = 500
            mock_response.text = "Server error"
            mock_response.json.side_effect = ValueError("Not JSON")
        return mock_response

    mock_execute.side_effect = side_effect_function
    payload = {
        "endpoints": [
            "https://api.example.com/success",
            "https://api.example.com/partial",
            "https://api.example.com/error",
        ]
    }
    data = post_execute(client, payload["endpoints"], status_code=207)
    assert data["success"] is False
    assert data["successful"] == 1
    assert data["warnings"] == 1
    assert data["failed"] == 1


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_only_207_returns_207(mock_execute, client):
    """
    Test /execute returns 207 when all responses are 207.
    """
    mock_response = MagicMock()
    mock_response.status_code = 207
    mock_response.json.return_value = {"partial": "success"}
    mock_execute.return_value = mock_response
    data = post_execute(
        client,
        ["https://api.example.com/task1", "https://api.example.com/task2"],
        status_code=207,
    )
    assert data["success"] is True
    assert data["successful"] == 0
    assert data["warnings"] == 2
    assert data["failed"] == 0
