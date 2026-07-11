"""
Tests for retry integration in src/app.py POST /execute endpoint.

Verifies that:
- execute_endpoints() uses execute_with_retry (not execute) for POST requests.
- The retry parameters passed to execute_with_retry match the AppConfig values.
- The ExecutionSummary JSON shape is unchanged after the retry refactor.
"""

import json
from unittest.mock import MagicMock, patch

from src.config import config
from src.models import ExecutionResult, ExecutionStatus

# ---------------------------------------------------------------------------
# Test 1: POST /execute calls execute_with_retry with correct config params
# ---------------------------------------------------------------------------


@patch("src.app.HTTPExecutor.execute_with_retry")
def test_post_execute_calls_execute_with_retry(mock_retry, client):
    """
    POST /execute must delegate to execute_with_retry, not execute.
    The retry parameters must match the values from AppConfig.
    """
    ok_result = MagicMock(spec=ExecutionResult)
    ok_result.to_dict.return_value = {
        "endpoint": "http://a.com",
        "method": "POST",
        "status_code": 200,
        "response": {"result": "ok"},
        "timestamp": "2024-01-01T00:00:00",
        "attempts": 1,
    }
    ok_result.status = ExecutionStatus.SUCCESS

    mock_retry.return_value = ([ok_result], [], [])

    response = client.post(
        "/execute",
        data=json.dumps({"endpoints": ["http://a.com"]}),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )

    assert response.status_code == 200
    assert mock_retry.called, "execute_with_retry must be called for POST /execute"

    _, call_kwargs = mock_retry.call_args
    assert call_kwargs["max_attempts"] == config.retry_max_attempts
    assert call_kwargs["backoff_base_seconds"] == config.retry_backoff_base_seconds
    assert call_kwargs["backoff_max_seconds"] == config.retry_backoff_max_seconds


# ---------------------------------------------------------------------------
# Test 2: ExecutionSummary JSON shape is unchanged
# ---------------------------------------------------------------------------


@patch("src.app.HTTPExecutor.execute_with_retry")
def test_execute_summary_shape_unchanged(mock_retry, client):
    """
    Introducing execute_with_retry must not change the contract of the /execute response.
    All previously existing keys must still be present with correct semantics.
    """
    ok_result = MagicMock(spec=ExecutionResult)
    ok_result.to_dict.return_value = {
        "endpoint": "http://a.com",
        "method": "POST",
        "status_code": 200,
        "response": {"result": "ok"},
        "timestamp": "2024-01-01T00:00:00",
        "attempts": 1,
    }
    ok_result.status = ExecutionStatus.SUCCESS

    mock_retry.return_value = ([ok_result], [], [])

    response = client.post(
        "/execute",
        data=json.dumps({"endpoints": ["http://a.com"]}),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )

    data = json.loads(response.data)

    required_keys = {
        "success",
        "total_endpoints",
        "successful",
        "warnings",
        "failed",
        "results",
        "details",
        "execution_mode",
        "timestamp",
        "email_notification",
    }
    assert required_keys.issubset(
        set(data.keys())
    ), f"Missing keys in response: {required_keys - set(data.keys())}"

    assert data["success"] is True
    assert data["total_endpoints"] == 1
    assert data["successful"] == 1
    assert data["failed"] == 0
    assert data["warnings"] == 0
    assert isinstance(data["results"], list)
    assert isinstance(data["details"], dict)
    assert "warnings" in data["details"]
    assert "errors" in data["details"]
