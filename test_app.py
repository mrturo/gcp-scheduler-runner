"""Pytest test suite for the Flask application."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from app import app as flask_app
from app import execute_request
from config import load_endpoints_from_env, parse_curl_config


@pytest.fixture
def app():
    """Create Flask test app."""
    flask_app.config.update({"TESTING": True})
    # Temporarily disable API_KEY for tests unless explicitly testing authentication
    import config

    original_api_key = config.API_KEY
    config.API_KEY = None
    # Also update the app module's import
    import app as app_module

    app_module.API_KEY = None
    yield flask_app
    # Restore original API_KEY
    config.API_KEY = original_api_key
    app_module.API_KEY = original_api_key


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


def test_index_endpoint(client):
    """Test the root endpoint returns server information."""
    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "GCP Scheduler Runner"
    assert data["status"] == "running"
    assert "endpoints" in data
    assert "configured_endpoints" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
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
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Task 3 executed successfully"
    assert data["data"] == payload


@patch("app.execute_request")
def test_execute_endpoints_get(mock_execute, client):
    """Test execute endpoint with GET request."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    response = client.get("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "success" in data
    assert "results" in data


@patch("app.execute_request")
def test_execute_endpoints_post_with_json(mock_execute, client):
    """Test execute endpoint with POST and JSON payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": ["http://localhost:5000/task1"],
        "default_payload": {"key": "value"},
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 1


@patch("app.execute_request")
def test_execute_endpoints_post_without_json(mock_execute, client):
    """Test execute endpoint with POST but no JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    response = client.post("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "success" in data


@patch("requests.request")
def test_execute_request_simple_url(mock_request):
    """Test execute_request with a simple URL string."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    result = execute_request("http://example.com")
    assert result.status_code == 200
    mock_request.assert_called_once()


@patch("requests.request")
def test_execute_request_with_config(mock_request):
    """Test execute_request with full configuration."""
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
    result = execute_request(config)
    assert result.status_code == 200


@patch("requests.request")
def test_execute_request_with_json_body(mock_request):
    """Test execute_request with JSON body."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_request.return_value = mock_response

    config = {
        "url": "http://example.com/api",
        "method": "POST",
        "json": {"data": "value"},
    }
    result = execute_request(config)
    assert result.status_code == 201


@patch("requests.request")
def test_execute_request_with_body(mock_request):
    """Test execute_request with body (non-JSON)."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_request.return_value = mock_response

    config = {"url": "http://example.com/api", "method": "POST", "body": "raw data"}
    result = execute_request(config)
    assert result.status_code == 201


@patch("requests.request")
def test_execute_request_with_default_payload(mock_request):
    """Test execute_request with default payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response

    config = {"url": "http://example.com/api", "method": "POST"}
    default_payload = {"default_key": "default_value"}
    result = execute_request(config, default_payload)
    assert result.status_code == 200


@patch("app.execute_request")
def test_execute_endpoints_with_error(mock_execute, client):
    """Test execute endpoint when request fails."""
    mock_execute.side_effect = requests.exceptions.RequestException("Connection error")

    response = client.get("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["failed"] > 0
    assert len(data["errors"]) > 0


@patch("app.execute_request")
def test_execute_endpoints_with_non_json_response(mock_execute, client):
    """Test execute endpoint when response is not JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Not JSON")
    mock_response.text = "Plain text response"
    mock_execute.return_value = mock_response

    response = client.get("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "results" in data


@patch("app.execute_request")
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
    with pytest.raises(ValueError, match="ENDPOINTS environment variable is not set"):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_invalid_json(mock_getenv):
    """Test load_endpoints_from_env with invalid JSON."""
    mock_getenv.return_value = "not valid json"
    with pytest.raises(ValueError, match="Error parsing ENDPOINTS"):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_not_list(mock_getenv):
    """Test load_endpoints_from_env when ENDPOINTS is not a list."""
    mock_getenv.return_value = '{"url": "http://example.com"}'
    with pytest.raises(ValueError, match="ENDPOINTS must be a JSON array"):
        load_endpoints_from_env()


@patch("os.getenv")
def test_load_endpoints_from_env_empty_list(mock_getenv):
    """Test load_endpoints_from_env with empty list."""
    mock_getenv.return_value = "[]"
    with pytest.raises(ValueError, match="ENDPOINTS array cannot be empty"):
        load_endpoints_from_env()


@patch("app.load_endpoints_from_env")
def test_index_uses_load_endpoints(mock_load, client):
    """Index should call load_endpoints_from_env when no endpoints are set."""
    mock_load.return_value = ["http://example.com"]
    import app as app_module

    # Ensure module-level variable is None so the function calls loader
    app_module.ENDPOINTS_TO_EXECUTE = None

    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["configured_endpoints"] == 1


@patch("app.load_endpoints_from_env")
def test_execute_uses_load_endpoints(mock_load, client):
    """Execute endpoint should call load_endpoints_from_env when no endpoints provided."""
    mock_load.return_value = ["http://localhost:5000/task1"]
    import app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None

    response = client.get("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "results" in data


@patch("app.load_endpoints_from_env")
def test_index_handles_missing_endpoints(mock_load, client):
    """Index should handle missing ENDPOINTS by returning 0 configured endpoints."""
    mock_load.side_effect = ValueError("no endpoints")
    import app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None

    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["configured_endpoints"] == 0


@patch("app.load_endpoints_from_env")
def test_execute_handles_missing_endpoints(mock_load, client):
    """Execute should handle missing ENDPOINTS by returning zero total_endpoints."""
    mock_load.side_effect = ValueError("no endpoints")
    import app as app_module

    app_module.ENDPOINTS_TO_EXECUTE = None

    response = client.get("/execute")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["total_endpoints"] == 0


@patch("app.execute_request")
def test_execute_endpoints_parallel_mode(mock_execute, client):
    """Test execute endpoint with parallel execution mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": [
            "http://localhost:5000/task1",
            "http://localhost:5000/task2",
            "http://localhost:5000/task3",
        ],
        "parallel": True,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 3
    assert data["successful"] == 3
    assert data["execution_mode"] == "parallel"


@patch("app.execute_request")
def test_execute_endpoints_sequential_mode(mock_execute, client):
    """Test execute endpoint with sequential execution mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": [
            "http://localhost:5000/task1",
            "http://localhost:5000/task2",
        ],
        "parallel": False,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 2
    assert data["execution_mode"] == "sequential"


@patch("app.execute_request")
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
            "http://localhost:5000/task1",
            "http://localhost:5000/task2",
            "http://localhost:5000/task3",
            "http://localhost:5000/task4",
        ],
        "parallel": True,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is False
    assert data["total_endpoints"] == 4
    assert data["successful"] == 2
    assert data["failed"] == 2
    assert data["execution_mode"] == "parallel"


@patch("app.execute_request")
def test_execute_endpoints_parallel_with_max_workers(mock_execute, client):
    """Test parallel execution with custom max_workers."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": [f"http://localhost:5000/task{i}" for i in range(1, 6)],
        "parallel": True,
        "max_workers": 3,
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["total_endpoints"] == 5
    assert data["execution_mode"] == "parallel"


@patch("app.execute_request")
def test_execute_endpoints_single_endpoint_sequential(mock_execute, client):
    """Test that single endpoint execution uses sequential mode."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": ["http://localhost:5000/task1"],
        "parallel": True,  # Request parallel but should use sequential
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["execution_mode"] == "sequential"


@patch("app.execute_request")
def test_execute_endpoints_parallel_default_behavior(mock_execute, client):
    """Test that parallel execution is the default for multiple endpoints."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    payload = {
        "endpoints": [
            "http://localhost:5000/task1",
            "http://localhost:5000/task2",
        ]
        # No "parallel" key specified - should default to True
    }
    response = client.post(
        "/execute",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["execution_mode"] == "parallel"


# API Key Authentication Tests
def test_api_key_missing():
    """Test that missing API key is rejected when API_KEY is configured."""
    # Create app with API_KEY enabled
    test_app = flask_app
    test_app.config.update({"TESTING": True})

    # Set API_KEY temporarily
    import app as app_module
    import config

    original_key = config.API_KEY
    config.API_KEY = "test_key_12345"
    app_module.API_KEY = "test_key_12345"

    with test_app.test_client() as client:
        response = client.post("/execute")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "error" in data
        assert "Missing X-API-Key header" in data["error"]

    # Restore
    config.API_KEY = original_key
    app_module.API_KEY = original_key


def test_api_key_invalid():
    """Test that invalid API key is rejected."""
    # Create app with API_KEY enabled
    test_app = flask_app
    test_app.config.update({"TESTING": True})

    # Set API_KEY temporarily
    import app as app_module
    import config

    original_key = config.API_KEY
    config.API_KEY = "correct_key_12345"
    app_module.API_KEY = "correct_key_12345"

    with test_app.test_client() as client:
        response = client.post("/execute", headers={"X-API-Key": "wrong_key"})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "error" in data
        assert "Invalid X-API-Key" in data["error"]

    # Restore
    config.API_KEY = original_key
    app_module.API_KEY = original_key


@patch("app.execute_request")
def test_api_key_valid(mock_execute):
    """Test that valid API key allows access."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"result": "success"}
    mock_execute.return_value = mock_response

    # Create app with API_KEY enabled
    test_app = flask_app
    test_app.config.update({"TESTING": True})

    # Set API_KEY temporarily
    import app as app_module
    import config

    original_key = config.API_KEY
    config.API_KEY = "correct_key_12345"
    app_module.API_KEY = "correct_key_12345"

    with test_app.test_client() as client:
        response = client.post("/execute", headers={"X-API-Key": "correct_key_12345"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "success" in data or "results" in data

    # Restore
    config.API_KEY = original_key
    app_module.API_KEY = original_key


def test_resolve_template_vars_success(monkeypatch):
    """Test template variable resolution with valid environment variables."""
    from config import resolve_template_vars

    monkeypatch.setenv("SECRET_TOKEN", "my_secret_123")
    monkeypatch.setenv("API_URL", "https://api.example.com")

    input_text = '{"url": "${API_URL}/endpoint", "headers": {"Authorization": "Bearer ${SECRET_TOKEN}"}}'
    result = resolve_template_vars(input_text)

    assert (
        result
        == '{"url": "https://api.example.com/endpoint", "headers": {"Authorization": "Bearer my_secret_123"}}'
    )


def test_resolve_template_vars_missing_variable(monkeypatch):
    """Test template variable resolution fails with missing environment variable."""
    from config import resolve_template_vars

    input_text = '{"token": "${MISSING_VAR}"}'

    with pytest.raises(ValueError, match="Template variable.*MISSING_VAR.*not defined"):
        resolve_template_vars(input_text)


def test_resolve_template_vars_no_templates():
    """Test template variable resolution with no templates returns unchanged text."""
    from config import resolve_template_vars

    input_text = '{"url": "https://api.example.com", "method": "GET"}'
    result = resolve_template_vars(input_text)

    assert result == input_text


def test_resolve_template_vars_non_string():
    """Test template variable resolution with non-string input returns unchanged."""
    from config import resolve_template_vars

    assert resolve_template_vars(None) is None
    assert resolve_template_vars(123) == 123
    assert resolve_template_vars({"key": "value"}) == {"key": "value"}


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

    with pytest.raises(
        ValueError, match="Template variable.*UNDEFINED_TOKEN.*not defined"
    ):
        load_endpoints_from_env()
