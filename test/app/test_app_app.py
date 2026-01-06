"""
Tests for src/app.py endpoints and integration.
"""
import json
import os
import sys
from unittest.mock import patch

from test.helpers_extra import create_mock_response, post_execute

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock all HTTP requests to always raise ConnectionError
@pytest.fixture(autouse=True)
def mock_requests_request(monkeypatch):
    """Mock requests.request to always raise a ConnectionError."""
    def raise_conn_error(*args, **kwargs):
        raise requests.ConnectionError("Mocked connection error")
    monkeypatch.setattr("requests.request", raise_conn_error)

def test_index_endpoint(client):
    """
    Test the root endpoint returns server information.
    Args:
        client: Flask test client.
    """
    response = client.get("/", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["name"] == "GCP Scheduler Runner"
    assert data["status"] == "running"
    assert "endpoints" in data
    assert "configured_endpoints" in data

def test_health_endpoint(client):
    """
    Test the health check endpoint.
    Args:
        client: Flask test client.
    """
    response = client.get("/health", headers={"X-API-Key": "test-api-key-123"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert "timestamp" in data

def test_task1_endpoint(client):
    """
    Test task1 endpoint.
    Args:
        client: Flask test client.
    """
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
    """
    Test task2 endpoint.
    Args:
        client: Flask test client.
    """
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
    """
    Test task3 endpoint.
    Args:
        client: Flask test client.
    """
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

@patch("src.http_executor.requests.request")
def test_post_execute(mock_request, client):
    """
    Test post_execute helper function.
    Args:
        client: Flask test client.
    """
    mock_request.return_value = create_mock_response()
    data = post_execute(
        client,
        ["https://api.example.com/task1", "https://api.example.com/task2"],
        status_code=200,
    )
    assert data["success"] is True
    assert data["failed"] == 0
