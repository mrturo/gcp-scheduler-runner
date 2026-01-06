"""Test script for validating Flask application endpoints."""

import json

import requests

# Base URL for the API
BASE_URL = "http://localhost:3000"


def test_execute_with_default_endpoints():
    """Test using the default configured endpoints"""
    print("\n=== Test 1: Execute default endpoints ===")
    response = requests.post(f"{BASE_URL}/execute", timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_execute_with_simple_urls():
    """Test with simple URL strings"""
    print("\n=== Test 2: Execute simple URLs ===")
    payload = {
        "endpoints": ["http://localhost:3000/task1", "http://localhost:3000/task2"],
        "default_payload": {"user_id": 123, "action": "test"},
    }
    response = requests.post(f"{BASE_URL}/execute", json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_execute_with_complex_configs():
    """Test with complex configurations (cURL-like)"""
    print("\n=== Test 3: Execute with complex configurations ===")
    payload = {
        "endpoints": [
            {
                "url": "http://localhost:3000/task1",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Custom-Header": "value123",
                },
                "json": {"user_id": 456, "priority": "high"},
                "timeout": 10,
            },
            {
                "url": "http://localhost:3000/task2",
                "method": "POST",
                "headers": {"Authorization": "Bearer fake-token"},
                "json": {"status": "active"},
            },
            {"url": "http://localhost:3000/health", "method": "GET"},
        ]
    }
    response = requests.post(f"{BASE_URL}/execute", json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_execute_with_mixed_configs():
    """Test mixing simple URLs and complex configurations"""
    print("\n=== Test 4: Mix simple and complex configs ===")
    payload = {
        "endpoints": [
            "http://localhost:3000/task1",
            {
                "url": "http://localhost:3000/task2",
                "method": "POST",
                "headers": {"X-Request-ID": "12345"},
                "json": {"data": "complex"},
            },
            "http://localhost:3000/task3",
        ],
        "default_payload": {"default_key": "default_value"},
    }
    response = requests.post(f"{BASE_URL}/execute", json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_health():
    """Test the health check endpoint"""
    print("\n=== Test 5: Health Check ===")
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    try:
        test_health()
        test_execute_with_default_endpoints()
        test_execute_with_simple_urls()
        test_execute_with_complex_configs()
        test_execute_with_mixed_configs()
    except requests.exceptions.RequestException as exc:
        print(f"\nError during tests: {exc}")
        print("Ensure the server is running: python app.py")
