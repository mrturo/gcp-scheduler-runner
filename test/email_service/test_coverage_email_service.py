"""
Coverage tests for src/email_service.py (EmailNotificationService,
EmailTemplateBuilder, AttachmentBuilder).
"""

import os
import sys
from datetime import datetime
from test.helpers_extra import make_email_config
from src.email_service import EmailNotificationService, EmailTemplateBuilder, AttachmentBuilder
from src.models import ExecutionSummary

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_email_template_builder_add_warnings_section_empty():
    """
    Test EmailTemplateBuilder.add_warnings_section with empty list.
    """
    builder = EmailTemplateBuilder()
    result = builder.add_warnings_section([])
    assert result is builder

def test_attachment_builder_create_warning_attachments():
    """
    Test AttachmentBuilder.create_warning_attachments returns correct attachments.
    """
    warnings = [
        {
            "endpoint": "http://example.com/warning1",
            "method": "POST",
            "status_code": 207,
            "timestamp": datetime.now().isoformat(),
            "response": {"partial": "success"},
        },
        {
            "endpoint": "http://example.com/warning2",
            "method": "GET",
            "status_code": 207,
            "timestamp": datetime.now().isoformat(),
            "response": {"warnings": ["warn1"]},
        },
    ]
    attachments = AttachmentBuilder.create_warning_attachments(warnings)
    assert len(attachments) == 2
    assert all(att.get_content_type() == "application/json" for att in attachments)

def test_attachment_builder_create_error_attachments():
    """
    Test AttachmentBuilder.create_error_attachments returns correct attachments.
    """
    errors = [
        {
            "endpoint": "http://example.com/error1",
            "method": "POST",
            "error": "Connection timeout",
        },
        {
            "endpoint": "http://example.com/error2",
            "method": "GET",
            "error": "404 Not Found",
        },
    ]
    attachments = AttachmentBuilder.create_error_attachments(errors)
    assert len(attachments) == 2
    assert all(att.get_content_type() == "application/json" for att in attachments)

def test_email_notification_service_get_status_and_color():
    """
    Test EmailNotificationService._determine_status_text_and_color for all summary types.
    """
    email_config = make_email_config()
    service = EmailNotificationService(email_config)
    summary_errors = ExecutionSummary(
        total_endpoints=1,
        successful=0,
        warnings=0,
        failed=1,
        results=[],
        details={"warnings": [], "errors": [{"error": "Failed"}]},
    )
    status, color = getattr(service, "_determine_status_text_and_color")(summary_errors)
    assert "FAILED" in status
    assert color == "#dc3545"
    summary_warnings = ExecutionSummary(
        total_endpoints=1,
        successful=0,
        warnings=1,
        failed=0,
        results=[],
        details={"warnings": [{"warning": "207"}], "errors": []},
    )
    status, color = getattr(service, "_determine_status_text_and_color")(summary_warnings)
    assert "WARNING" in status
    assert color == "#ff9800"
    summary_success = ExecutionSummary(
        total_endpoints=1,
        successful=1,
        warnings=0,
        failed=0,
        results=[{"result": "ok"}],
        details={"warnings": [], "errors": []},
    )
    status, color = getattr(service, "_determine_status_text_and_color")(summary_success)
    assert "SUCCESS" in status
    assert color == "#28a745"
