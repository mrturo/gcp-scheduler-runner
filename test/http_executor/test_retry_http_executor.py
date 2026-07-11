"""
Tests for HTTPExecutor.execute_with_retry() and _partition_errors_for_retry().

Verifies that:
- Only failed (ERROR) endpoints are retried, not successful ones.
- Attempt counts are stamped correctly on each ExecutionResult.
- max_attempts=1 behaves identically to execute() with no retry.
- Time budget enforcement stops retries before exceeding the deadline.
- Parse-failure errors (endpoint="endpoint_N") are permanent and not retried.
- Non-str/non-dict configs hit the ValueError branch in _partition_errors_for_retry.
"""

from unittest.mock import call, patch

from src.http_executor import HTTPExecutor
from src.models import ExecutionResult, ExecutionStatus


def _make_ok(url: str) -> ExecutionResult:
    """Create a SUCCESS ExecutionResult for the given URL."""
    return ExecutionResult(
        endpoint=url,
        method="POST",
        status_code=200,
        response={"result": "ok"},
        status=ExecutionStatus.SUCCESS,
    )


def _make_err(url: str) -> ExecutionResult:
    """Create an ERROR ExecutionResult for the given URL."""
    return ExecutionResult(
        endpoint=url,
        method="UNKNOWN",
        status_code=0,
        response=None,
        status=ExecutionStatus.ERROR,
        error=f"Error on {url}: connection refused",
    )


# ---------------------------------------------------------------------------
# Test 1: one of three endpoints fails on attempt 1, succeeds on attempt 2
# ---------------------------------------------------------------------------


@patch("src.http_executor.time.sleep")
@patch("src.http_executor.time.monotonic", return_value=0.0)
@patch.object(HTTPExecutor, "execute")
def test_retry_succeeds_on_second_attempt(mock_execute, _mock_mono, mock_sleep):
    """
    3 endpoints: a and c succeed immediately; b fails on attempt 1, succeeds on attempt 2.
    Verifies: a and c are invoked exactly once; b is invoked twice; attempts counts correct.
    """
    endpoints = ["http://a.com", "http://b.com", "http://c.com"]

    a_ok = _make_ok("http://a.com")
    b_err = _make_err("http://b.com")
    c_ok = _make_ok("http://c.com")
    b_retry_ok = _make_ok("http://b.com")

    mock_execute.side_effect = [
        ([a_ok, c_ok], [], [b_err]),  # attempt 1: a+c succeed, b fails
        ([b_retry_ok], [], []),  # attempt 2: b succeeds
    ]

    executor = HTTPExecutor()
    results, warnings, errors = executor.execute_with_retry(
        endpoints, parallel=False, max_attempts=2
    )

    # execute() called twice total
    assert mock_execute.call_count == 2

    # First call: all 3 endpoints
    first_call_endpoints = mock_execute.call_args_list[0][0][0]
    assert len(first_call_endpoints) == 3

    # Second call: only the failing endpoint
    second_call_endpoints = mock_execute.call_args_list[1][0][0]
    assert second_call_endpoints == ["http://b.com"]

    # All 3 ultimately successful, no errors
    assert len(results) == 3
    assert not errors
    assert not warnings

    # Attempt numbers stamped correctly
    assert a_ok.attempts == 1
    assert c_ok.attempts == 1
    assert b_retry_ok.attempts == 2

    # Sleep called once between the two attempts
    assert mock_sleep.call_count == 1


# ---------------------------------------------------------------------------
# Test 2: endpoint fails on every attempt — exhausts max_attempts
# ---------------------------------------------------------------------------


@patch("src.http_executor.time.sleep")
@patch("src.http_executor.time.monotonic", return_value=0.0)
@patch.object(HTTPExecutor, "execute")
def test_all_attempts_exhausted(mock_execute, _mock_mono, mock_sleep):
    """
    Single endpoint fails on all 3 attempts.
    Verifies: execute() called 3 times; error in final_errors with attempts==3.
    """
    endpoints = ["http://fail.com"]

    errors_per_attempt = [_make_err("http://fail.com") for _ in range(3)]
    mock_execute.side_effect = [([], [], [err]) for err in errors_per_attempt]

    executor = HTTPExecutor()
    results, warnings, errors = executor.execute_with_retry(
        endpoints, parallel=False, max_attempts=3
    )

    assert mock_execute.call_count == 3
    assert not results
    assert not warnings
    assert len(errors) == 1
    assert errors[0].attempts == 3

    # Two sleeps: after attempt 1 and after attempt 2
    assert mock_sleep.call_count == 2
    # Exponential backoff: base * 2^0 = 2, base * 2^1 = 4
    assert mock_sleep.call_args_list == [call(2.0), call(4.0)]


# ---------------------------------------------------------------------------
# Test 3: max_attempts=1 — behaves identically to execute(), no retry
# ---------------------------------------------------------------------------


@patch("src.http_executor.time.sleep")
@patch.object(HTTPExecutor, "execute")
def test_max_attempts_one_no_retry(mock_execute, mock_sleep):
    """
    With max_attempts=1, execute_with_retry makes exactly one call and returns as-is.
    No sleep should occur.
    """
    endpoints = ["http://a.com", "http://b.com"]

    a_ok = _make_ok("http://a.com")
    b_err = _make_err("http://b.com")
    mock_execute.return_value = ([a_ok], [], [b_err])

    executor = HTTPExecutor()
    results, _, errors = executor.execute_with_retry(endpoints, parallel=False, max_attempts=1)

    assert mock_execute.call_count == 1
    assert mock_sleep.call_count == 0
    assert len(results) == 1
    assert len(errors) == 1
    assert errors[0].attempts == 1


# ---------------------------------------------------------------------------
# Test 4: time budget exceeded — retry is skipped
# ---------------------------------------------------------------------------


@patch("src.http_executor.time.sleep")
@patch("src.http_executor.time.monotonic")
@patch.object(HTTPExecutor, "execute")
def test_time_budget_stops_retry(mock_execute, mock_monotonic, mock_sleep):
    """
    When elapsed + backoff >= 1800s, the retry loop stops immediately.
    No sleep should occur and the error stays in final_errors.
    """
    endpoints = ["http://a.com"]
    err = _make_err("http://a.com")

    mock_execute.return_value = ([], [], [err])
    # start_time=0, then elapsed=1799 when checked → 1799 + 2 >= 1800 → stop
    mock_monotonic.side_effect = [0.0, 1799.0]

    executor = HTTPExecutor()
    _, _, errors = executor.execute_with_retry(
        endpoints, parallel=False, max_attempts=3, backoff_base_seconds=2.0
    )

    assert mock_execute.call_count == 1  # budget cut before second attempt
    assert mock_sleep.call_count == 0
    assert len(errors) == 1
    assert errors[0].attempts == 1


# ---------------------------------------------------------------------------
# Test 5: parse-failure errors (endpoint="endpoint_N") are permanent
# ---------------------------------------------------------------------------


@patch("src.http_executor.time.sleep")
@patch.object(HTTPExecutor, "execute")
def test_parse_failure_is_permanent_error(mock_execute, mock_sleep):
    """
    Errors whose endpoint field is 'endpoint_N' (produced by parse failures inside
    execute_single_endpoint) cannot be correlated back to a raw config and must NOT
    be retried — they go directly to final_errors.
    """
    endpoints = [{"url": "http://a.com"}]

    parse_err = ExecutionResult(
        endpoint="endpoint_0",
        method="UNKNOWN",
        status_code=0,
        response=None,
        status=ExecutionStatus.ERROR,
        error="Error on endpoint_0: invalid config",
    )
    mock_execute.return_value = ([], [], [parse_err])

    executor = HTTPExecutor()
    _, _, errors = executor.execute_with_retry(endpoints, parallel=False, max_attempts=3)

    assert mock_execute.call_count == 1  # parse failures are permanent, no retry
    assert mock_sleep.call_count == 0
    assert len(errors) == 1
    assert errors[0].endpoint == "endpoint_0"
    assert errors[0].attempts == 1


# ---------------------------------------------------------------------------
# Test 6: _partition_errors_for_retry — ValueError branch (non-str/dict config)
# ---------------------------------------------------------------------------


def test_partition_errors_invalid_config_type_is_skipped():
    """
    When a pending config has an invalid type (not str/dict), from_config raises
    ValueError. The except branch silently skips it, and the corresponding error
    result (endpoint_N) becomes a permanent error since it has no URL key match.
    """
    # 12345 is an int — EndpointConfig.from_config(12345) raises ValueError
    pending_configs = [12345]

    # Simulate the error result execute() would produce for a parse failure
    parse_err = ExecutionResult(
        endpoint="endpoint_0",
        method="UNKNOWN",
        status_code=0,
        response=None,
        status=ExecutionStatus.ERROR,
        error="Error on endpoint_0: Invalid endpoint configuration type: <class 'int'>",
    )

    executor = HTTPExecutor()
    # pylint: disable=protected-access
    retriable_configs, retriable_errors, permanent_errors = (
        executor._partition_errors_for_retry([parse_err], pending_configs)
    )
    # pylint: enable=protected-access

    assert not retriable_configs
    assert not retriable_errors
    assert len(permanent_errors) == 1
    assert permanent_errors[0].endpoint == "endpoint_0"
