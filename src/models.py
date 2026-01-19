"""Data models and constants for the application.

This module defines core data structures and constants used across the application.
Follows Single Responsibility Principle (SRP) - handles only data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionStatus(Enum):
    """Enum for execution status classification."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class HTTPMethod(Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class EndpointConfig:
    """Configuration for a single endpoint execution.

    Supports both simple URL strings and full cURL-like configuration.
    """

    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    json_data: Optional[Dict] = None
    params: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30

    @classmethod
    def from_config(cls, config):
        """
        Create EndpointConfig from various input formats.

        Args:
            config: String URL or dict configuration

        Returns:
            EndpointConfig instance
        """
        if isinstance(config, str):
            return cls(url=config, method="POST")

        if isinstance(config, dict):
            return cls(
                url=config.get("url"),
                method=config.get("method", "POST").upper(),
                headers=config.get("headers", {}),
                body=config.get("body"),
                json_data=config.get("json"),
                params=config.get("params", {}),
                timeout=config.get("timeout", 30),
            )

        raise ValueError(f"Invalid endpoint configuration type: {type(config)}")


@dataclass
class ExecutionResult:
    """Result of a single endpoint execution."""

    endpoint: str
    method: str
    status_code: int
    response: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        result = {
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "response": self.response,
            "timestamp": self.timestamp,
        }
        if self.error:
            result["error"] = self.error
        return result

    @classmethod
    def from_error(cls, endpoint: str, error_message: str):
        """Create error result."""
        return cls(
            endpoint=endpoint,
            method="UNKNOWN",
            status_code=0,
            response=None,
            error=error_message,
            status=ExecutionStatus.ERROR,
        )

    @classmethod
    def from_response(cls, endpoint: str, method: str, response):
        """
        Create result from HTTP response.

        Args:
            endpoint: Endpoint URL
            method: HTTP method used
            response: requests.Response object

        Returns:
            ExecutionResult with appropriate status classification
        """
        try:
            response_data = response.json()
        except (ValueError, Exception):  # pylint: disable=broad-except
            response_data = response.text

        status = cls._classify_status(response.status_code)
        error = None if status != ExecutionStatus.ERROR else f"HTTP {response.status_code}"

        return cls(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            response=response_data,
            status=status,
            error=error,
        )

    @staticmethod
    def _classify_status(status_code: int) -> ExecutionStatus:
        """
        Classify HTTP status code into execution status.

        Args:
            status_code: HTTP status code

        Returns:
            ExecutionStatus enum value
        """
        if status_code == 207:
            return ExecutionStatus.WARNING
        if 200 <= status_code < 300:
            return ExecutionStatus.SUCCESS
        return ExecutionStatus.ERROR


@dataclass
class ExecutionSummaryBase:
    """Base summary for multiple endpoint executions (max 7 attributes)."""

    total_endpoints: int
    successful: int
    warnings: int
    failed: int
    results: List[Dict] = field(default_factory=list)
    details: Dict[str, List[Dict]] = field(default_factory=lambda: {"warnings": [], "errors": []})
    execution_mode: str = "sequential"


@dataclass
class ExecutionSummary(ExecutionSummaryBase):
    """Summary of multiple endpoint executions (extended)."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    email_notification: Dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was completely successful."""
        return self.failed == 0 and self.warnings == 0

    @property
    def has_errors(self) -> bool:
        """Check if execution has errors."""
        return self.failed > 0

    @property
    def has_warnings(self) -> bool:
        """Check if execution has warnings."""
        return self.warnings > 0

    def get_http_status(self) -> int:
        """
        Determine appropriate HTTP status code for the execution.

        Returns:
            500 if errors, 207 if warnings, 200 if success
        """
        if self.has_errors:
            return 500
        if self.has_warnings:
            return 207
        return 200

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "total_endpoints": self.total_endpoints,
            "successful": self.successful,
            "warnings": self.warnings,
            "failed": self.failed,
            "results": self.results,
            "details": self.details,
            "execution_mode": self.execution_mode,
            "timestamp": self.timestamp,
            "email_notification": self.email_notification,
        }


@dataclass
class EmailConfig:
    """Email notification configuration."""

    smtp_host: str
    smtp_port: int
    smtp_user: Optional[str]
    smtp_password: Optional[str]
    email_from: Optional[str]
    email_to: Optional[str]

    def is_configured(self) -> bool:
        """Check if email configuration is complete."""
        return all(
            [
                self.smtp_user,
                self.smtp_password,
                self.email_to,
                self.smtp_host,
                self.smtp_port,
            ]
        )


# Constants for email status
EMAIL_STATUS_SUCCESS = "✅ SUCCESS"
EMAIL_STATUS_WARNING = "⚠️ COMPLETED WITH WARNINGS"
EMAIL_STATUS_FAILED = "❌ FAILED"

# Color constants for email HTML
COLOR_SUCCESS = "#28a745"
COLOR_WARNING = "#ff9800"
COLOR_ERROR = "#dc3545"
