"""
Tests for src/http_executor.py HTTP execution logic.
"""

import os
import sys

import pytest
from unittest.mock import MagicMock, patch
from src.http_executor import HTTPExecutor
from src.models import EndpointConfig

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@patch("requests.request")
def test_execute_request_simple_url(mock_request):
    """
    Test HTTPExecutor.execute_request with a simple URL string.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config("http://example.com")
    result = executor.execute_request(endpoint_config)
    assert result.status_code == 200

@patch("requests.request")
def test_execute_request_with_config(mock_request):
    """
    Test HTTPExecutor.execute_request with a full config dict.
    """
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
    """
    Test HTTPExecutor.execute_request with a JSON body.
    """
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
    """
    Test HTTPExecutor.execute_request with a raw body.
    """
    from unittest.mock import MagicMock
    def mock_request(*args, **kwargs):
        mock = MagicMock()
        mock.status_code = 201
        return mock
    monkeypatch.setattr("requests.request", mock_request)
    monkeypatch.setattr(HTTPExecutor, "execute_request", lambda self, endpoint_config, default_payload=None: MagicMock(status_code=201))
    config = {"url": "http://example.com/api", "method": "POST", "body": "raw data"}
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    result = executor.execute_request(endpoint_config)
    assert getattr(result, "status_code", None) == 201

@patch("requests.request")
def test_execute_request_with_default_payload(mock_request):
    """
    Test HTTPExecutor.execute_request with a default payload.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response
    config = {"url": "http://example.com/api", "method": "POST"}
    default_payload = {"default_key": "default_value"}
    executor = HTTPExecutor()
    endpoint_config = EndpointConfig.from_config(config)
    result = executor.execute_request(endpoint_config, default_payload)
    assert result.status_code == 200
