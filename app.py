"""Flask application for executing multiple HTTP endpoints."""

from concurrent.futures import (  # pylint: disable=no-name-in-module
    ThreadPoolExecutor, as_completed)
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, jsonify, request

from config import API_KEY, PORT, load_endpoints_from_env

app = Flask(__name__)

# Endpoints to execute (loaded from .env via config.py on demand)
ENDPOINTS_TO_EXECUTE = None


def require_api_key(f):
    """
    Decorator to require X-API-Key header authentication.

    If API_KEY is set in environment, validates the request header.
    If API_KEY is not set, allows all requests (useful for development).
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if API_KEY:
            provided_key = request.headers.get("X-API-Key")
            if not provided_key:
                return (
                    jsonify(
                        {
                            "error": "Missing X-API-Key header",
                            "message": "This endpoint requires authentication",
                        }
                    ),
                    401,
                )
            if provided_key != API_KEY:
                return (
                    jsonify(
                        {
                            "error": "Invalid X-API-Key",
                            "message": "The provided API key is not valid",
                        }
                    ),
                    403,
                )
        return f(*args, **kwargs)

    return decorated_function


def execute_request(endpoint_config, default_payload=None):
    """
    Execute an HTTP request based on the endpoint configuration.

    Supported configuration:
    - url: endpoint URL (required)
    - method: GET, POST, PUT, DELETE, PATCH (default: POST)
    - headers: dict of headers
    - body/json: request body
    - params: query parameters
    - timeout: timeout in seconds (default: 30)
    """
    # Support simple URL string or full configuration
    if isinstance(endpoint_config, str):
        endpoint_config = {"url": endpoint_config, "method": "POST"}

    endpoint_url = endpoint_config.get("url")
    http_method = endpoint_config.get("method", "POST").upper()
    headers = endpoint_config.get("headers", {})
    body = endpoint_config.get("body") or endpoint_config.get("json")
    params = endpoint_config.get("params", {})
    timeout = endpoint_config.get("timeout", 30)

    # If no body is defined, use the default payload
    if body is None and default_payload:
        body = default_payload

    # Prepare kwargs for requests
    request_kwargs = {"timeout": timeout, "headers": headers, "params": params}

    # Add body according to its type
    if body is not None:
        if isinstance(body, dict):
            request_kwargs["json"] = body
        else:
            request_kwargs["data"] = body

    # Execute the request
    response = requests.request(http_method, endpoint_url, **request_kwargs)

    return response


def _execute_single_endpoint(endpoint_idx, endpoint_config, default_payload):
    """
    Execute a single endpoint and return its result or error.

    This function is designed to be called by ThreadPoolExecutor.
    Returns a tuple: (success: bool, result: dict)
    """
    endpoint_name = None
    try:
        if isinstance(endpoint_config, str):
            endpoint_name = endpoint_config
        else:
            endpoint_name = endpoint_config.get("url", f"endpoint_{endpoint_idx}")

        print(f"Executing: {endpoint_name}")
        response = execute_request(endpoint_config, default_payload)

        # Try to parse the response
        try:
            response_data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            response_data = response.text

        result = {
            "endpoint": endpoint_name,
            "method": (
                endpoint_config.get("method", "POST")
                if isinstance(endpoint_config, dict)
                else "POST"
            ),
            "status_code": response.status_code,
            "response": response_data,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"Completed: {endpoint_name} - Status: {response.status_code}")
        return (True, result)

    except (requests.exceptions.RequestException, ValueError) as exc:
        error_msg = (
            f"Error on {endpoint_name or f'endpoint_{endpoint_idx}'}: {str(exc)}"
        )
        print(error_msg)
        error = {
            "endpoint": endpoint_name or f"endpoint_{endpoint_idx}",
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }
        return (False, error)


@app.route("/", methods=["GET"])
@require_api_key
def index():
    """Root route with server information"""
    configured = 0
    try:
        configured = (
            len(ENDPOINTS_TO_EXECUTE)
            if ENDPOINTS_TO_EXECUTE is not None
            else len(load_endpoints_from_env())
        )
    except ValueError:
        configured = 0

    return jsonify(
        {
            "name": "GCP Scheduler Runner",
            "status": "running",
            "version": "1.0.0",
            "endpoints": {
                "/": "GET - Server information",
                "/health": "GET - Health check",
                "/execute": "GET/POST - Execute configured endpoints",
                "/task1": "POST - Example endpoint 1",
                "/task2": "POST - Example endpoint 2",
                "/task3": "POST - Example endpoint 3",
            },
            "configured_endpoints": configured,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/execute", methods=["POST", "GET"])
@require_api_key
def execute_endpoints():
    """
    Main endpoint that executes a series of other endpoints.

    Supports parallel execution via ThreadPoolExecutor by default.
    To disable parallel execution, set "parallel": false in the request body.

    Example payload:
    {
        "endpoints": [
            {
                "url": "https://api.example.com/users",
                "method": "POST",
                "headers": {"Authorization": "Bearer token123"},
                "json": {"name": "John"},
                "timeout": 30
            },
            {
                "url": "https://api.example.com/orders",
                "method": "GET",
                "params": {"status": "active"}
            },
            "http://simple-url.com/endpoint"
        ],
        "default_payload": {"key": "value"},
        "parallel": true,
        "max_workers": 10
    }
    """
    results = []
    errors = []

    data = request.get_json(silent=True) or {}
    endpoints = data.get("endpoints")
    if endpoints is None:
        try:
            endpoints = (
                ENDPOINTS_TO_EXECUTE
                if ENDPOINTS_TO_EXECUTE is not None
                else load_endpoints_from_env()
            )
        except ValueError:
            endpoints = []
    default_payload = data.get("default_payload") or data.get("payload")
    parallel = data.get("parallel", True)  # Default to parallel execution
    max_workers = data.get("max_workers", min(10, len(endpoints) or 1))

    if parallel and len(endpoints) > 1:
        # Parallel execution using ThreadPoolExecutor
        print(f"🚀 Execution mode: PARALLEL (max_workers={max_workers})")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(
                    _execute_single_endpoint, idx, config, default_payload
                ): idx
                for idx, config in enumerate(endpoints)
            }

            # Collect results as they complete
            for future in as_completed(future_to_idx):
                success, result_or_error = future.result()
                if success:
                    results.append(result_or_error)
                else:
                    errors.append(result_or_error)
    else:
        # Sequential execution (original behavior)
        print("🔄 Execution mode: SEQUENTIAL")
        for endpoint_idx, endpoint_config in enumerate(endpoints):
            success, result_or_error = _execute_single_endpoint(
                endpoint_idx, endpoint_config, default_payload
            )
            if success:
                results.append(result_or_error)
            else:
                errors.append(result_or_error)

    return jsonify(
        {
            "success": len(errors) == 0,
            "total_endpoints": len(endpoints),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "execution_mode": (
                "parallel" if parallel and len(endpoints) > 1 else "sequential"
            ),
        }
    )


# Example endpoints for testing
@app.route("/task1", methods=["POST"])
@require_api_key
def task1():
    """Example endpoint 1"""
    data = request.get_json() or {}
    return jsonify(
        {
            "message": "Task 1 executed successfully",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/task2", methods=["POST"])
@require_api_key
def task2():
    """Example endpoint 2"""
    data = request.get_json() or {}
    return jsonify(
        {
            "message": "Task 2 executed successfully",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/task3", methods=["POST"])
@require_api_key
def task3():
    """Example endpoint 3"""
    data = request.get_json() or {}
    return jsonify(
        {
            "message": "Task 3 executed successfully",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


def print_server_info():  # pragma: no cover
    """Print server startup information."""
    print(f"\n🚀 Server started at http://0.0.0.0:{PORT}")
    endpoints = ENDPOINTS_TO_EXECUTE
    if endpoints is None:
        try:
            endpoints = load_endpoints_from_env()
        except ValueError:
            endpoints = []

    print(f"📋 Configured endpoints: {len(endpoints)}")
    for idx, endpoint in enumerate(endpoints, 1):
        if isinstance(endpoint, str):
            print(f"   {idx}. {endpoint}")
        else:
            method = endpoint.get("method", "POST")
            url = endpoint.get("url", "N/A")
            print(f"   {idx}. [{method}] {url}")
    print()


if __name__ == "__main__":  # pragma: no cover
    print_server_info()
    app.run(debug=True, host="0.0.0.0", port=PORT)
