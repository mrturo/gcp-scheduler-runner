"""
Full coverage tests for src/http_executor.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.http_executor import HTTPExecutor
from src.models import EndpointConfig, ExecutionStatus

@pytest.mark.parametrize(
    "body,expected_json,expected_data",
    [
        (None, {"default_key": "default_value"}, None),
        ({"a": 1}, {"a": 1}, None),
        ("raw string", None, "raw string"),
    ],
)
@patch("src.http_executor.requests.request")
def test_execute_request_body_handling(
    mock_request, body, expected_json, expected_data
):
    """Test execute_request handles body, json, and default payload correctly."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response
    config = {"url": "http://example.com/api", "method": "POST"}
    executor = HTTPExecutor()
    config_for_test = dict(config)
    if body is None:
        endpoint_config = EndpointConfig.from_config(config_for_test)
        default_payload = {"default_key": "default_value"}
    elif isinstance(body, dict):
        config_for_test["json"] = body
        endpoint_config = EndpointConfig.from_config(config_for_test)
        default_payload = None
    else:
        config_for_test["body"] = body
        endpoint_config = EndpointConfig.from_config(config_for_test)
        default_payload = None
    executor.execute_request(endpoint_config, default_payload)
    call_kwargs = mock_request.call_args[1] if mock_request.call_args else {}
    assert call_kwargs.get("json") == expected_json
    assert call_kwargs.get("data") == expected_data

@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_single_endpoint_error_branch(_mock_execute):
    """Test execute_single_endpoint handles errors correctly."""
    class FakeResult:  # pylint: disable=too-few-public-methods
        """Fake result object for testing error paths."""
        status = ExecutionStatus.ERROR
        error = "Error on endpoint_0: Request failed"
    with patch(
        "src.models.ExecutionResult.from_response", return_value=FakeResult()
    ):
        def error_request(*args, **kwargs):
            raise RuntimeError("Request failed")  # Use specific exception
        with patch("requests.request", side_effect=error_request):
            executor = HTTPExecutor()
            status, result = executor.execute_single_endpoint(
                0, {"url": "bad-url"}
            )
            assert status == ExecutionStatus.ERROR
            assert "Error on" in result.error

@patch("src.http_executor.HTTPExecutor.execute_single_endpoint")
def test_execute_sequential_error_branch(mock_single):
    """Test execute_sequential handles errors correctly."""
    mock_single.return_value = (ExecutionStatus.ERROR, MagicMock(error="fail"))
    executor = HTTPExecutor()
    endpoints = ["http://fail.com"]
    results, warnings, errors = executor.execute_sequential(endpoints)
    assert len(errors) == 1
    assert not results
    assert not warnings

@patch("src.http_executor.HTTPExecutor.execute_single_endpoint")
def test_execute_parallel_error_branch(mock_single):
    """Test execute_parallel handles errors correctly."""
    mock_single.return_value = (ExecutionStatus.ERROR, MagicMock(error="fail"))
    executor = HTTPExecutor()
    endpoints = ["http://fail.com"]
    results, warnings, errors = executor.execute_parallel(endpoints)
    assert len(errors) == 1
    assert not results
    assert not warnings
