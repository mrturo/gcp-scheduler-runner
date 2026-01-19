"""Tests for src/email_service.py (EmailConfig, EmailNotificationService, ExecutionSummary)."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from src.email_service import EmailConfig, EmailNotificationService, ExecutionSummary

"""Tests for src/email_service.py (EmailConfig, EmailNotificationService, ExecutionSummary).
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from src.email_service import EmailConfig, EmailNotificationService, ExecutionSummary

class DummySMTP:
    """
    Dummy SMTP class for mocking email sending in tests.
    """
    def __init__(self, *a, sent_messages=None, **kw):
        self.sent_messages = sent_messages if sent_messages is not None else []
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    def starttls(self):
        pass
    def login(self, user, pwd):
        pass
    def send_message(self, msg):
        self.sent_messages.append(msg)

@pytest.mark.parametrize(
    "test_mode,query_string,body_value",
    [
        (True, "?test_mode=true", None),
        ("true", "", "true"),
        (True, "", True),
    ],
)
def test_execute_endpoints_email_subject_variants(client, monkeypatch, test_mode, query_string, body_value):
    """
    Test email subject variants for /execute endpoint with different test_mode values.
    """
    sent_messages = []
    class DummySMTPLocal(DummySMTP):
        def __init__(self, *a, **kw):
            super().__init__(*a, sent_messages=sent_messages, **kw)
    monkeypatch.setattr("smtplib.SMTP", DummySMTPLocal)
    monkeypatch.setenv("EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password123")
    class DummyResult:
        def __init__(self):
            self.endpoint = "https://api.example.com/test"
            self.method = "GET"
            self.status_code = 200
            self.timestamp = datetime.now().isoformat()
        def to_dict(self):
            return {
                "endpoint": self.endpoint,
                "method": self.method,
                "status_code": self.status_code,
                "timestamp": self.timestamp,
            }
    monkeypatch.setattr(
        "src.http_executor.HTTPExecutor.execute",
        lambda self, endpoints, parallel=True, default_payload=None: ([DummyResult()], [], []),
    )
    if query_string:
        response = client.post(
            f"/execute{query_string}",
            data=json.dumps({"endpoints": ["https://api.example.com/test"], "send_email": True}),
            content_type="application/json",
            headers={"X-API-Key": "test-api-key-123"},
        )
    else:
        body = {"endpoints": ["https://api.example.com/test"], "send_email": True}
        if body_value is not None:
            body["test_mode"] = body_value
        response = client.post(
            "/execute",
            data=json.dumps(body),
            content_type="application/json",
            headers={"X-API-Key": "test-api-key-123"},
        )
    assert response.status_code == 200
    assert sent_messages, "No se envió ningún mensaje de correo"
    subject = sent_messages[0]["Subject"]
    assert "Test Execution Report" in subject, f"Subject incorrecto: {subject}"

def test_send_email_notification_missing_smtp_user():
    """
    Test send_notification returns error if smtp_user is missing.
    """
    email_config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user=None,
        smtp_password="test_password",
        email_from="test@gmail.com",
        email_to="recipient@example.com",
    )
    summary = ExecutionSummary(
        total_endpoints=3,
        successful=3,
        warnings=0,
        failed=0,
        results=[],
        details={"warnings": [], "errors": []},
    )
    service = EmailNotificationService(email_config)
    result = service.send_notification(summary, execution_context="test")
    assert result["email_sent"] is False
    assert "Email configuration incomplete" in result["error"]

def test_send_email_notification_missing_smtp_password():
    """
    Test send_notification returns error if smtp_password is missing.
    """
    email_config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="test@gmail.com",
        smtp_password=None,
        email_from="test@gmail.com",
        email_to="recipient@example.com",
    )
    summary = ExecutionSummary(
        total_endpoints=3,
        successful=2,
        warnings=1,
        failed=0,
        results=[],
        details={"warnings": [{"endpoint": "http://example.com"}], "errors": []},
    )
    service = EmailNotificationService(email_config)
    result = service.send_notification(summary, execution_context="test")
    assert result["email_sent"] is False
    assert "Email configuration incomplete" in result["error"]

def test_send_email_notification_missing_email_to():
    email_config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="test@gmail.com",
        smtp_password="test_password",
        email_from="test@gmail.com",
        email_to=None,
    )
    summary = ExecutionSummary(
        total_endpoints=3,
        successful=2,
        warnings=0,
        failed=1,
        results=[],
        details={"warnings": [], "errors": [{"endpoint": "http://example.com/error"}]},
    )
    service = EmailNotificationService(email_config)
    result = service.send_notification(summary, execution_context="test")
    assert result["email_sent"] is False
    assert "Email configuration incomplete" in result["error"]

def test_send_email_notification_uses_smtp_user_as_from():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        email_config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="test_password",
            email_from=None,
            email_to="recipient@example.com",
        )
        summary = ExecutionSummary(
            total_endpoints=1,
            successful=1,
            warnings=0,
            failed=0,
            results=[],
            details={"warnings": [], "errors": []},
            execution_mode="sequential",
        )
        service = EmailNotificationService(email_config)
        result = service.send_notification(summary, execution_context="test")
        assert result["email_sent"] is True
        assert result["from"] == "test@gmail.com"
        sent_message = mock_server.send_message.call_args[0][0]
        assert "Test Execution Report" in sent_message["Subject"]

def test_send_email_notification_with_errors():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        email_config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="test_password",
            email_from="test@gmail.com",
            email_to="recipient@example.com",
        )
        summary = ExecutionSummary(
            total_endpoints=2,
            successful=1,
            warnings=0,
            failed=1,
            results=[
                {
                    "endpoint": "https://api.example.com/success",
                    "method": "GET",
                    "status_code": 200,
                    "timestamp": "2026-01-19T10:00:00",
                }
            ],
            details={
                "warnings": [],
                "errors": [
                    {
                        "endpoint": "https://api.example.com/failed",
                        "error": "Connection timeout",
                        "timestamp": "2026-01-19T10:01:00",
                    }
                ],
            },
            execution_mode="parallel",
        )
        service = EmailNotificationService(email_config)
        result = service.send_notification(summary, execution_context="test")
        assert result["email_sent"] is True
        assert result["attachments"] == 2
        mock_server.send_message.assert_called_once()
        sent_message = mock_server.send_message.call_args[0][0]
        assert "Test Execution Report" in sent_message["Subject"]
        assert sent_message.is_multipart()
        parts = list(sent_message.walk())
        assert len(parts) >= 4

def test_send_email_notification_smtp_exception():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP connection failed")
        email_config = EmailConfig(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="test_password",
            email_from="test@gmail.com",
            email_to="recipient@example.com",
        )
        summary = ExecutionSummary(
            total_endpoints=1,
            successful=1,
            warnings=0,
            failed=0,
            results=[],
            details={"warnings": [], "errors": []},
            execution_mode="sequential",
        )
        service = EmailNotificationService(email_config)
        result = service.send_notification(summary, execution_context="test")
        assert result["email_sent"] is False
        assert "SMTP connection failed" in result["error"]
