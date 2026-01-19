"""Helpers for test assertions to avoid code duplication."""


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
