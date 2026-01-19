"""Email notification service module.

This module handles email notifications with HTML formatting and attachments.
Follows Single Responsibility Principle (SRP) - handles only email notifications.
"""

import json
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from src.models import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    EMAIL_STATUS_FAILED,
    EMAIL_STATUS_SUCCESS,
    EMAIL_STATUS_WARNING,
    EmailConfig,
    ExecutionSummary,
)


class EmailTemplateBuilder:
    """Builds HTML email templates for execution reports.

    Follows Builder Pattern for complex HTML construction.
    """

    def __init__(self):
        """Initialize template builder."""
        self.html_parts = []

    def add_header(self, _status_text, _color):
        """Add email header with status (no-op, kept for interface compatibility)."""
        return self

    def add_results_section(self, results: List[Dict]):
        """Add successful results section."""
        if not results:
            return self

        self.html_parts.append("<h3 style='color: #28a745;'>✅ Successful Executions</h3><ul>")

        for result in results:
            self.html_parts.append(
                f"""
                <li>
                    <strong>{result['endpoint']}</strong> [{result['method']}]
                    - Status: {result['status_code']}
                    <br><small>Timestamp: {result['timestamp']}</small>
                </li>
                """
            )

        self.html_parts.append("</ul>")
        return self

    def add_warnings_section(self, warnings: List[Dict]):
        """Add warnings section for HTTP 207 responses."""
        if not warnings:
            return self

        self.html_parts.append(
            (
                "<div style='background-color: #fff3cd; border-left: 4px solid #ff9800; "
                "padding: 15px; margin: 20px 0;'>"
                "<h3 style='color: #ff9800; margin-top: 0;'>⚠️ Partial Success (HTTP 207)</h3>"
                "<p style='margin-top: 0;'><strong>These endpoints returned status 207, "
                "indicating some of their internal tasks failed."
                "</strong></p>"
                "<ul style='margin-bottom: 0;'>"
            )
        )

        for warning in warnings:
            response_text = str(warning.get("response", "N/A"))
            response_preview = response_text[:200] if len(response_text) > 200 else response_text

            self.html_parts.append(
                f"""
                <li style="color: #856404;">
                    <strong>{warning['endpoint']}</strong> [{warning['method']}]
                    - Status: {warning['status_code']}
                    <br><small>Timestamp: {warning['timestamp']}</small>
                    <br><small>Response preview: {response_preview}...</small>
                </li>
                """
            )

        self.html_parts.append("</ul></div>")
        return self

    def add_errors_section(self, errors: List[Dict]):
        """Add errors section."""
        if not errors:
            return self

        self.html_parts.append("<h3 style='color: #dc3545;'>❌ Errors</h3><ul>")

        for error in errors:
            error_msg = error.get("error", "Unknown error")
            self.html_parts.append(
                f"""
                <li style="color: #dc3545;">
                    <strong>{error['endpoint']}</strong>
                    <br>Error: {error_msg}
                    <br><small>Timestamp: {error['timestamp']}</small>
                </li>
                """
            )

        self.html_parts.append("</ul>")
        return self

    def build(self) -> str:
        """Build and return complete HTML content."""
        self.html_parts.append("</body></html>")
        return "".join(self.html_parts)


class AttachmentBuilder:
    """Builds email attachments from execution results.

    Follows Builder Pattern for attachment creation.
    """

    @staticmethod
    def sanitize_filename(endpoint: str, max_length: int = 50) -> str:
        """
        Sanitize endpoint URL to create valid filename.

        Args:
            endpoint: Endpoint URL
            max_length: Maximum filename length

        Returns:
            Sanitized filename string
        """
        return (
            endpoint.replace("https://", "")
            .replace("http://", "")
            .replace("/", "_")
            .replace(":", "_")[:max_length]
        )

    @staticmethod
    def create_json_attachment(data: Dict, filename: str) -> MIMEApplication:
        """
        Create JSON attachment from data.

        Args:
            data: Dictionary to convert to JSON
            filename: Attachment filename

        Returns:
            MIMEApplication attachment object
        """
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        attachment = MIMEApplication(json_data.encode("utf-8"), _subtype="json")
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        return attachment

    @classmethod
    def create_result_attachments(cls, results: List[Dict]) -> List[MIMEApplication]:
        """Create attachments for successful results."""
        attachments = []
        for idx, result in enumerate(results, 1):
            endpoint_name = result.get("endpoint", f"endpoint_{idx}")
            safe_name = cls.sanitize_filename(endpoint_name)
            filename = f"{idx:02d}_{safe_name}_result.json"
            attachments.append(cls.create_json_attachment(result, filename))
        return attachments

    @classmethod
    def create_warning_attachments(cls, warnings: List[Dict]) -> List[MIMEApplication]:
        """Create attachments for warnings."""
        attachments = []
        for idx, warning in enumerate(warnings, 1):
            endpoint_name = warning.get("endpoint", f"endpoint_warning_{idx}")
            safe_name = cls.sanitize_filename(endpoint_name)
            filename = f"WARNING_{idx:02d}_{safe_name}_207.json"
            attachments.append(cls.create_json_attachment(warning, filename))
        return attachments

    @classmethod
    def create_error_attachments(cls, errors: List[Dict]) -> List[MIMEApplication]:
        """Create attachments for errors."""
        attachments = []
        for idx, error in enumerate(errors, 1):
            endpoint_name = error.get("endpoint", f"endpoint_error_{idx}")
            safe_name = cls.sanitize_filename(endpoint_name)
            filename = f"ERROR_{idx:02d}_{safe_name}.json"
            attachments.append(cls.create_json_attachment(error, filename))
        return attachments


class EmailNotificationService:
    """Service for sending email notifications.

    Follows Facade Pattern to simplify email sending complexity.
    """

    def __init__(self, email_config: EmailConfig):
        """
        Initialize email service with configuration.

        Args:
            email_config: EmailConfig with SMTP settings
        """
        self.config = email_config

    def get_config(self) -> EmailConfig:
        """
        Return the current email configuration.
        """
        return self.config

    def _determine_status_text_and_color(self, summary: ExecutionSummary):
        """
        Determine email status text and color based on execution results.

        Args:
            summary: ExecutionSummary object

        Returns:
            Tuple of (status_text, color)
        """
        if summary.has_errors:
            return EMAIL_STATUS_FAILED, COLOR_ERROR
        if summary.has_warnings:
            return EMAIL_STATUS_WARNING, COLOR_WARNING
        return EMAIL_STATUS_SUCCESS, COLOR_SUCCESS

    def _build_email_message(
        self, summary: ExecutionSummary, execution_context: str = "manual"
    ) -> MIMEMultipart:
        """
        Build complete MIME email message.

        Args:
            summary: ExecutionSummary object

        Returns:
            MIMEMultipart message ready to send
        """
        status_text, color = self._determine_status_text_and_color(summary)

        # Determine subject prefix by context
        if execution_context == "test":  # pragma: no cover
            subject_prefix = "Test Execution Report"
        elif execution_context == "scheduler":  # pragma: no cover
            subject_prefix = "Scheduled Execution Report"
        else:  # pragma: no cover
            subject_prefix = "Manual Execution Report"

        # Build HTML content
        html_content = (
            EmailTemplateBuilder()
            .add_header(status_text, color)
            .add_results_section(summary.results)
            .add_warnings_section(summary.details.get("warnings", []))
            .add_errors_section(summary.details.get("errors", []))
            .build()
        )

        # Create MIME message
        message = MIMEMultipart("mixed")
        message["Subject"] = f"GCP Scheduler Runner - {subject_prefix} - {status_text}"
        message["From"] = self.config.email_from or self.config.smtp_user
        message["To"] = self.config.email_to

        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Attach JSON files
        for attachment in AttachmentBuilder.create_result_attachments(summary.results):
            message.attach(attachment)

        for attachment in AttachmentBuilder.create_warning_attachments(
            summary.details.get("warnings", [])
        ):
            message.attach(attachment)

        for attachment in AttachmentBuilder.create_error_attachments(
            summary.details.get("errors", [])
        ):
            message.attach(attachment)

        return message

    def send_notification(
        self, summary: ExecutionSummary, execution_context: str = "manual"
    ) -> Dict:
        """
        Send email notification with execution summary.

        Args:
            summary: ExecutionSummary object with execution results

        Returns:
            Dictionary with send status and details
        """
        if not self.config.is_configured():
            return {
                "email_sent": False,
                "error": (
                    "Email configuration incomplete (SMTP_USER, "
                    "SMTP_PASSWORD, or EMAIL_TO missing)"
                ),
            }

        try:
            message = self._build_email_message(summary, execution_context=execution_context)

            # Count total attachments
            total_attachments = (
                len(summary.results)
                + len(summary.details.get("warnings", []))
                + len(summary.details.get("errors", []))
            )

            # Send email via SMTP
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                # Garantiza que smtp_user y smtp_password sean str para mypy
                smtp_user = self.config.smtp_user or ""
                smtp_password = self.config.smtp_password or ""
                server.login(smtp_user, smtp_password)
                server.send_message(message)

            return {
                "email_sent": True,
                "recipient": self.config.email_to,
                "from": self.config.email_from or self.config.smtp_user,
                "attachments": total_attachments,
            }

        except Exception as exc:  # pylint: disable=broad-except
            return {
                "email_sent": False,
                "error": str(exc),
            }
