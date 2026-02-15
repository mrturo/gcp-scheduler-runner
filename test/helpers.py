"""Helpers for test assertions to avoid code duplication."""

from src.email_service import ExecutionSummary


def empty_execution_summary():
    """Returns a standard empty ExecutionSummary for test deduplication."""
    return ExecutionSummary(
        total_endpoints=0,
        successful=0,
        warnings=0,
        failed=0,
        results=[],
        details={"warnings": [], "errors": []},
        execution_mode="sequential",
    )


def assert_execution_summary_zero_endpoints():
    """Asserts that an empty ExecutionSummary returns HTTP 200."""
    summary = empty_execution_summary()
    assert summary.get_http_status() == 200


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
    assert data["success"] == success
    assert data["warnings"] == warnings
    assert data["successful"] == successful
    assert data["failed"] == failed


# Endpoint result helpers for test deduplication


def _base_endpoint_result(successful, warnings, failed, warnings_list=None, errors_list=None):
    return {
        "total_endpoints": 3,
        "successful": successful,
        "warnings": warnings,
        "failed": failed,
        "results": [],
        "details": {
            "warnings": warnings_list if warnings_list is not None else [],
            "errors": errors_list if errors_list is not None else [],
        },
    }


def endpoint_result_all_success():
    """Helper to generate a successful endpoint result."""
    return _base_endpoint_result(3, 0, 0)


def endpoint_result_one_warning():
    """Helper to generate an endpoint result with one warning."""
    return _base_endpoint_result(2, 1, 0, warnings_list=[{"endpoint": "http://example.com"}])


def endpoint_result_one_error():
    """Helper to generate an endpoint result with one error."""
    return _base_endpoint_result(2, 0, 1, errors_list=[{"endpoint": "http://example.com/error"}])
