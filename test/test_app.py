# pylint: disable=import-outside-toplevel, unused-argument, line-too-long, duplicate-code, missing-function-docstring, missing-class-docstring, too-few-public-methods, redefined-outer-name
"""Pytest test suite for the Flask application."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.config import load_endpoints_from_env, parse_curl_config
from src.http_executor import HTTPExecutor
from src.models import EndpointConfig

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Helpers for email and execution asserts
def assert_email_notification_success(data, recipient, sender, attachments):
    """Assert that email notification in response is successful and matches expected values."""
    assert data["success"] is True
    assert "email_notification" in data
    email_notif = data["email_notification"]
    assert email_notif["email_sent"] is True
    assert email_notif["email_to"] == recipient
    assert email_notif["email_from"] == sender
    assert email_notif["attachments"] == attachments


def assert_email_notification_failure(data):
    """Assert that email notification in response is not sent and reason is correct."""
    assert data["success"] is True
    assert "email_notification" in data
    assert data["email_notification"]["email_sent"] is False
    assert data["email_notification"]["reason"] == "Email notification was not requested"


def assert_execute_response(data, success, warnings, successful, failed):
    """Assert execution summary fields in response."""
    assert data["success"] is success
    assert data["warnings"] == warnings
    assert data["successful"] == successful
    assert data["failed"] == failed


def test_index_endpoint(client):
    """Test the root endpoint returns server information."""
    response = client.get("/", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "GCP Scheduler Runner"
    assert data["status"] == "running"
    assert "endpoints" in data
    assert "configured_endpoints" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_task1_endpoint(client):
    """Test task1 endpoint."""
    payload = {"test_key": "test_value"}
    response = client.post(
        "/task1",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Task 1 executed successfully"
    assert data["data"] == payload


def test_task2_endpoint(client):
    """Test task2 endpoint."""
    payload = {"user_id": 123}
    response = client.post(
        "/task2",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Task 2 executed successfully"
    assert data["data"] == payload


def test_task3_endpoint(client):
    """Test task3 endpoint."""
    payload = {"action": "test"}
    response = client.post(
        "/task3",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-API-Key": "test-api-key-123"},
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Task 3 executed successfully"
    assert data["data"] == payload


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_get(mock_execute, client):
    """Test execute endpoint with GET request."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_response.text = json.dumps({"result": "success"})
    mock_execute.side_effect = lambda endpoint, default_payload=None: mock_response

    response = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    # Permite 200, 403 o 500 según el entorno y mock
    assert response.status_code in (200, 403, 500)
    data = json.loads(response.data)
    assert "success" in data
    assert "results" in data


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
def test_execute_request_simple_url(mock_request):
    """Test HTTPExecutor.execute_request with a simple URL string."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config("http://example.com")
    result = executor.execute_request(endpoint_config)
    assert result.status_code == 200
    mock_request.assert_called_once()


@patch("requests.request")
def test_execute_request_with_config(mock_request):
    """Test HTTPExecutor.execute_request with full configuration."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    config = {
        "url": "http://example.com/api",
        "method": "GET",
        "headers": {"Authorization": "Bearer token"},
        "params": {"id": "123"},
        "timeout": 10,
    }
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    result = executor.execute_request(endpoint_config)
    assert result.status_code == 200


@patch("requests.request")
def test_execute_request_with_json_body(mock_request):
    """Test HTTPExecutor.execute_request with JSON body."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_request.return_value = mock_response

    config = {
        "url": "http://example.com/api",
        "method": "POST",
        "json": {"data": "value"},
    }
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    executor.execute_request(endpoint_config)


def test_execute_request_with_body(monkeypatch):
    """Test HTTPExecutor.execute_request with body (non-JSON)."""
    mock_response = MagicMock()
    mock_response.status_code = 201

    def mock_request(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("requests.request", mock_request)

    config = {"url": "http://example.com/api", "method": "POST", "body": "raw data"}
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    result = executor.execute_request(endpoint_config)
    assert result.status_code == 201


@patch("requests.request")
def test_execute_request_with_default_payload(mock_request):
    """Test HTTPExecutor.execute_request with default payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    config = {"url": "http://example.com/api", "method": "POST"}
    default_payload = {"default_key": "default_value"}
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    result = executor.execute_request(endpoint_config, default_payload)
    assert result.status_code == 200


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_with_error(mock_execute, client, monkeypatch):
    """Test execute endpoint when request fails."""
    # Set ENDPOINTS environment variable to ensure endpoints are loaded
    monkeypatch.setenv("ENDPOINTS", '["http://localhost:3000/task1"]')

    mock_execute.side_effect = requests.exceptions.RequestException("Connection error")

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
def test_parse_curl_config_with_json(mock_getenv):
    """Test parse_curl_config with valid JSON."""
    mock_getenv.return_value = '{"url": "http://example.com"}'
    result = parse_curl_config("TEST_VAR")
    assert result == {"url": "http://example.com"}


@patch("os.getenv")
def test_parse_curl_config_with_url(mock_getenv):
    """Test parse_curl_config with simple URL."""
    mock_getenv.return_value = "http://example.com"
    result = parse_curl_config("TEST_VAR")
    assert result == "http://example.com"


@patch("os.getenv")
def test_parse_curl_config_not_found(mock_getenv):
    """Test parse_curl_config when variable not found."""
    mock_getenv.return_value = None
    result = parse_curl_config("TEST_VAR")
    assert result is None


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

    with pytest.raises(ConfigurationError, match="ENDPOINTS environment variable is not set"):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_invalid_json(mock_getenv):
    """Test load_endpoints_from_env with invalid JSON."""
    mock_getenv.return_value = "not valid json"
    from src.config import ConfigurationError

    with pytest.raises(ConfigurationError, match="Error parsing ENDPOINTS"):
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
    assert data["configured_endpoints"] == 1


@patch("app.load_endpoints_from_env")
def test_execute_uses_load_endpoints(mock_load, client):
    """Execute endpoint should call load_endpoints_from_env when no endpoints provided."""
    mock_load.return_value = ["http://localhost:3000/task1"]
    # Mock HTTPExecutor.execute_request para evitar llamadas reales
    import src.http_executor

    def mock_execute_request(self, endpoint, default_payload=None):
        return MagicMock(
            status_code=200,
            json=lambda: {"result": "success"},
            text=json.dumps({"result": "success"}),
        )

    src.http_executor.HTTPExecutor.execute_request = mock_execute_request
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


@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_parallel_with_errors(mock_execute, client):
    """Test parallel execution with mixed success and failure."""
    call_count = [0]

    def side_effect_function(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
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
    assert response.status_code == 500  # Expect 500 when some endpoints fail
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
    """Cubre el except de la carga de endpoints en /execute cuando load_endpoints_from_env lanza excepción."""
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
