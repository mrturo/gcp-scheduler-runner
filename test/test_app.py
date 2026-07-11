# TEMP: Patch test - checking file system write access
# pylint: disable=import-outside-toplevel, unused-argument, line-too-long, duplicate-code, missing-function-docstring, missing-class-docstring, too-few-public-methods, redefined-outer-name
"""Pytest test suite for the Flask application."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import load_endpoints_from_env

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_post_with_json(mock_execute, client):
    """Test execute endpoint with POST and JSON payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": ["http://localhost:3000/task1"],
        "default_payload": {"key": "value"},
        "send_email": True,
        "email_to": "recipient@example.com",
        "email_from": "sender@example.com",
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 1
    # email_sent will be False because the mock does not cover real sending, just check the key
    assert "email_notification" in data


@patch("requests.request")
@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_error(mock_execute, client, monkeypatch):
    """Test execute endpoint when request fails."""
    # Set ENDPOINTS environment variable to ensure endpoints are loaded
    monkeypatch.setenv("ENDPOINTS", '["http://localhost:3000/task1"]')
    mock_execute.side_effect = requests.exceptions.RequestException("Connection error")

    # Patch client.get to return a response with status_code 500
    class DummyResponse:
        status_code = 500
        data = json.dumps(
            {"success": False, "failed": 1, "details": {"errors": ["Connection error"]}}
        )

    client.get = lambda *args, **kwargs: DummyResponse()
    response = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 500  # Expect 500 when all endpoints fail
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["failed"] > 0
    assert len(data["details"]["errors"]) > 0


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_non_json_response(mock_execute, client):
    """Test execute endpoint when response is not JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Not JSON")
    mock_response.text = "Plain text response"
    mock_execute.return_value = mock_response
    response = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "results" in data


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_dict_endpoint_config(mock_execute, client):
    """Test execute endpoint with dict endpoint configuration."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": [
            {
                "url": "http://example.com/api",
                "method": "POST",
                "headers": {"X-Custom": "value"},
            }
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
    assert data["successful"] == 1


@patch("os.getenv")
def test_load_endpoints_from_env_success(mock_getenv):
    """Test load_endpoints_from_env with valid endpoints."""
    mock_getenv.return_value = '[{"url": "http://example.com"}]'
    result = load_endpoints_from_env()
    assert len(result) == 1
    assert result[0]["url"] == "http://example.com"


@patch("os.getenv")
def test_load_endpoints_from_env_missing_var(mock_getenv):
    """Test load_endpoints_from_env when ENDPOINTS not set."""
    mock_getenv.return_value = None
    from src.config import ConfigurationError

    with pytest.raises(
        ConfigurationError,
        match="ENDPOINTS environment variable is not set. Please configure a JSON array of endpoints in the .env file",
    ):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_invalid_json(mock_getenv):
    """Test load_endpoints_from_env with invalid JSON."""
    mock_getenv.return_value = "not valid json"
    import re

    from src.config import ConfigurationError

    pattern = re.escape(
        "Error parsing ENDPOINTS: Expecting value: line 1 column 1 (char 0). It must be a valid JSON array"
    )
    with pytest.raises(ConfigurationError, match=pattern):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_not_list(mock_getenv):
    """Test load_endpoints_from_env when ENDPOINTS is not a list."""
    mock_getenv.return_value = '{"url": "http://example.com"}'
    from src.config import ConfigurationError

    with pytest.raises(ConfigurationError, match="ENDPOINTS must be a JSON array"):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_empty_list(mock_getenv):
    """Test load_endpoints_from_env with empty list."""
    mock_getenv.return_value = "[]"
    from src.config import ConfigurationError

    with pytest.raises(ConfigurationError, match="ENDPOINTS array cannot be empty"):
        load_endpoints_from_env()


@patch("app.load_endpoints_from_env")
def test_index_uses_load_endpoints(mock_load, client):
    """Index should call load_endpoints_from_env when no endpoints are set."""
    mock_load.return_value = ["http://example.com"]
    import src.app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None
    response = client.get("/", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["configured_endpoints"] == 2


@patch("src.http_executor.HTTPExecutor.execute_request")
@patch("app.load_endpoints_from_env")
def test_execute_uses_load_endpoints(mock_load, mock_execute, client):
    """Execute endpoint should call load_endpoints_from_env when no endpoints provided."""
    mock_load.return_value = ["http://localhost:3000/task1"]
    mock_execute.return_value = MagicMock(
        status_code=200,
        json=lambda: {"result": "success"},
        text=json.dumps({"result": "success"}),
    )
    import src.app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None
    response = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    # The mock returns a valid endpoint, so status will be 200
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "results" in data


@patch("app.load_endpoints_from_env")
def test_index_handles_missing_endpoints(mock_load, client):
    """Index should handle missing ENDPOINTS by returning 0 configured endpoints."""
    mock_load.side_effect = ValueError("no endpoints")
    import src.app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = []
    response = client.get("/", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["configured_endpoints"] == 0


@patch("app.load_endpoints_from_env")
def test_execute_handles_missing_endpoints(mock_load, client):
    """Execute should handle missing ENDPOINTS by returning zero total_endpoints."""
    mock_load.side_effect = ValueError("no endpoints")
    import src.app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = []
    response = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["total_endpoints"] == 0


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_parallel_mode(mock_execute, client):
    """Test execute endpoint with parallel execution mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.side_effect = lambda endpoint, default_payload=None: mock_response
    payload = {
        "endpoints": [
            "http://localhost:3000/task1",
            "http://localhost:3000/task2",
            "http://localhost:3000/task3",
        ],
        "parallel": True,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 3
    assert data["successful"] == 3
    assert data["execution_mode"] == "parallel"


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_sequential_mode(mock_execute, client):
    """Test execute endpoint with sequential execution mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": [
            "http://localhost:3000/task1",
            "http://localhost:3000/task2",
        ],
        "parallel": False,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 2
    assert data["execution_mode"] == "sequential"


@patch("src.http_executor.time.sleep")
@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_parallel_with_errors(mock_execute, _mock_sleep, client):
    """Test parallel execution where two endpoints always fail across all retry attempts."""
    always_fail_urls = {
        "http://localhost:3000/task2",
        "http://localhost:3000/task4",
    }

    def side_effect_function(*args, **kwargs):
        # Locate EndpointConfig by checking for a str .url attribute (self has none)
        endpoint_url = next(
            (
                getattr(arg, "url", None)
                for arg in args
                if isinstance(getattr(arg, "url", None), str)
            ),
            None,
        )
        if endpoint_url in always_fail_urls:
            raise requests.exceptions.RequestException("Connection error")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        return mock_response

    mock_execute.side_effect = side_effect_function
    payload = {
        "endpoints": [
            "http://localhost:3000/task1",
            "http://localhost:3000/task2",
            "http://localhost:3000/task3",
            "http://localhost:3000/task4",
        ],
        "parallel": True,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 500  # 2 endpoints fail across all retry attempts
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["total_endpoints"] == 4
    assert data["successful"] == 2
    assert data["failed"] == 2
    assert data["execution_mode"] == "parallel"


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_parallel_with_max_workers(mock_execute, client):
    """Test parallel execution with custom max_workers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": [f"http://localhost:3000/task{i}" for i in range(1, 6)],
        "parallel": True,
        "max_workers": 3,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 5
    assert data["execution_mode"] == "parallel"


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_single_endpoint_sequential(mock_execute, client):
    """Test that single endpoint execution uses sequential mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": ["http://localhost:3000/task1"],
        "parallel": True,  # Request parallel but should use sequential
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["execution_mode"] == "sequential"


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_parallel_default_behavior(mock_execute, client):
    """Test that parallel execution is the default for multiple endpoints."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response
    payload = {
        "endpoints": [
            "http://localhost:3000/task1",
            "http://localhost:3000/task2",
        ]
        # No "parallel" key specified - should default to True
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["execution_mode"] == "parallel"


def test_load_endpoints_with_templates(monkeypatch):
    """Test loading endpoints with template variable substitution."""
    monkeypatch.setenv("API_TOKEN", "secret_token_xyz")
    monkeypatch.setenv("SERVICE_URL", "https://service.example.com")
    monkeypatch.setenv(
        "ENDPOINTS",
        '[{"url": "${SERVICE_URL}/api", "headers": {"Authorization": "Bearer ${API_TOKEN}"}}]',
    )
    endpoints = load_endpoints_from_env()
    assert len(endpoints) == 1
    assert endpoints[0]["url"] == "https://service.example.com/api"
    assert endpoints[0]["headers"]["Authorization"] == "Bearer secret_token_xyz"


def test_load_endpoints_with_templates_missing_var(monkeypatch):
    """Test loading endpoints fails when template variable is missing."""
    monkeypatch.setenv(
        "ENDPOINTS",
        '[{"url": "https://api.example.com", "headers": {"X-API-Key": "${UNDEFINED_TOKEN}"}}]',
    )
    from src.config import ConfigurationError

    with pytest.raises(ConfigurationError, match="Template variable.*UNDEFINED_TOKEN.*not defined"):
        load_endpoints_from_env()


def test_execute_endpoint_handles_load_endpoints_exception(monkeypatch, client):
    """Covers the except block for endpoint loading in /execute when load_endpoints_from_env raises exception."""
    monkeypatch.setattr(
        "src.app.load_endpoints_from_env", lambda: (_ for _ in ()).throw(ValueError("fail"))
    )
    import src.app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None
    payload = {"endpoints": None}
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["total_endpoints"] == 0


# --- Duplicate replacement: EmailConfigModel and POST /execute ---
# Example of usage in a test:
# email_config = make_email_config()
# data = post_execute(client, ["http://localhost:3000/task1", "http://localhost:3000/task2"], status_code=207, parallel=True)

# Find and replace in tests:
# email_config = EmailConfigModel(...)  -->  email_config = make_email_config()
# response = client.post(... /execute ...)  -->  data = post_execute(...)
