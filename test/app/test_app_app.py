"""
Tests for src/app.py endpoints and integration.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests
from src.app import app as flask_app

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def assert_execute_response(data, success, warnings, successful, failed):
    """
    Assert execution summary fields in response.
    Args:
        data (dict): Response data.
        success (bool): Expected success value.
        warnings (int): Expected warnings count.
        successful (int): Expected successful count.
        failed (int): Expected failed count.
    """
    assert data["success"] is success
    assert data["warnings"] == warnings
    assert data["successful"] == successful
    assert data["failed"] == failed

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

# ...continues with tests for /execute, API Key, and endpoint handling...
