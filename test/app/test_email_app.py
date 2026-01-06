"""
Tests for src/app.py related to email notification integration.
"""

from unittest.mock import MagicMock, patch
from test.helpers_extra import create_mock_response, post_execute_custom_payload
import pytest

@pytest.mark.parametrize(
    "send_email,expected_sent,expected_reason",
    [
        (True, True, None),
        (False, False, "Email notification was not requested"),
        (None, False, "Email notification was not requested"),
    ],
)
@patch("smtplib.SMTP")
@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_email_notification_variants(
    mock_execute, mock_smtp, client, send_email, expected_sent, expected_reason
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    Parametrized test for email notification scenarios.
    """
    mock_execute.return_value = create_mock_response()
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    payload = {"endpoints": ["https://api.example.com/test"], "test_mode": True}
    if send_email is not None:
        payload["send_email"] = send_email
    data = post_execute_custom_payload(client, payload)
    assert data["success"] is True
    assert "email_notification" in data
    assert data["email_notification"]["email_sent"] is expected_sent
    if not expected_sent:
        assert data["email_notification"]["reason"] == expected_reason

@pytest.mark.parametrize(
    "payload,expected_sent,expected_reason,expect_attachments",
    [
        (  # send_email True, adjuntos esperados
            {"endpoints": ["https://api.example.com/test"], "send_email": True, "test_mode": True},
            True,
            None,
            True,
        ),
        (  # send_email False
            {"endpoints": ["https://api.example.com/test"], "send_email": False, "test_mode": True},
            False,
            "Email notification was not requested",
            False,
        ),
        (  # send_email None (no presente)
            {"endpoints": ["https://api.example.com/test"], "test_mode": True},
            False,
            "Email notification was not requested",
            False,
        ),
    ],
)
@patch("smtplib.SMTP")
@patch("src.http_executor.HTTPExecutor.execute_request")
def test_execute_endpoints_email_notification_cases(
    mock_execute, mock_smtp, client, payload, expected_sent, expected_reason, expect_attachments
):  # pylint: disable=too-many-arguments,too-many-positional-arguments  # Required for pytest parametrization
    """
    Parametrized test for email notification scenarios, including adjuntos.
    """
    mock_execute.return_value = create_mock_response()
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    data = post_execute_custom_payload(client, payload)
    assert data["success"] is True
    assert "email_notification" in data
    assert data["email_notification"]["email_sent"] is expected_sent
    if not expected_sent:
        assert data["email_notification"]["reason"] == expected_reason
    if expect_attachments:
        assert "attachments" in data["email_notification"]
