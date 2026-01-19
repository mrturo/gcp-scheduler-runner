"""Configuration utilities for loading endpoints and settings from environment.

This module provides configuration classes and utilities that parse endpoint
configuration from environment variables. Configuration loading is performed
on demand to make the module easier to test.

Supports template variable substitution in ENDPOINTS using ${VAR_NAME} syntax.
This allows separating sensitive credentials from endpoint structure.

Follows Single Responsibility Principle (SRP) - handles only configuration.
"""

import json
import os
import re
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""


class ServerConfig:
    """Server configuration settings."""

    def __init__(self):
        self.port = int(os.getenv("PORT", "8080"))
        self.api_key = os.getenv("API_KEY")
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))

    def get_port(self) -> int:
        """Get configured server port."""
        return self.port

    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return self.api_key is not None


class EmailConfig:
    """Email configuration settings."""

    def __init__(self):
        email_address = os.getenv("EMAIL_ADDRESS")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = email_address
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_from = email_address
        self.email_to = email_address

    def is_configured(self) -> bool:
        """Check if email configuration is complete."""
        return all([self.smtp_user, self.smtp_password, self.email_to])

    def get_smtp_config(self) -> dict:
        """Get SMTP configuration as dictionary."""
        return {
            "host": self.smtp_host,
            "port": self.smtp_port,
            "user": self.smtp_user,
            "password": self.smtp_password,
        }


class AppConfig:
    """Application configuration singleton.

    Centralizes all application configuration in one place.
    Follows Singleton Pattern to ensure single source of truth.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.server = ServerConfig()
        self.email = EmailConfig()
        self._initialized = True

    @property
    def port(self) -> int:
        """Get server port."""
        return self.server.port

    @property
    def api_key(self) -> Optional[str]:
        """Get API key."""
        return self.server.api_key

    @property
    def request_timeout(self) -> int:
        """Get request timeout."""
        return self.server.request_timeout

    @property
    def smtp_host(self) -> str:
        """Get SMTP host."""
        return self.email.smtp_host

    @property
    def smtp_port(self) -> int:
        """Get SMTP port."""
        return self.email.smtp_port

    @property
    def smtp_user(self) -> Optional[str]:
        """Get SMTP user."""
        return self.email.smtp_user

    @property
    def smtp_password(self) -> Optional[str]:
        """Get SMTP password."""
        return self.email.smtp_password

    @property
    def email_from(self) -> Optional[str]:
        """Get email from address."""
        return self.email.email_from

    @property
    def email_to(self) -> Optional[str]:
        """Get email to address."""
        return self.email.email_to

    @property
    def is_email_configured(self) -> bool:
        """Check if email configuration is complete."""
        return self.email.is_configured()


# Global configuration instance
config = AppConfig()

# Backwards compatibility - expose as module-level variables
PORT = config.port
API_KEY = config.api_key
REQUEST_TIMEOUT = config.request_timeout
SMTP_HOST = config.smtp_host
SMTP_PORT = config.smtp_port
SMTP_USER = config.smtp_user
SMTP_PASSWORD = config.smtp_password
EMAIL_FROM = config.email_from
EMAIL_TO = config.email_to


class TemplateResolver:
    """Resolves template variables in strings using ${VAR_NAME} syntax.

    Follows Strategy Pattern for variable resolution.
    """

    @staticmethod
    def resolve(text: str) -> str:
        """
        Resolve template variables in text using ${VAR_NAME} syntax.

        Replaces all occurrences of ${VARIABLE_NAME} with the value from environment.
        Raises ConfigurationError if a referenced variable is not defined.

        Args:
            text: String containing template variables (e.g., '{"key": "${SECRET}"}')

        Returns:
            String with all template variables replaced with their values

        Raises:
            ConfigurationError: If referenced variable is not defined

        Example:
            >>> os.environ['TOKEN'] = 'secret123'
            >>> TemplateResolver.resolve('{"auth": "${TOKEN}"}')
            '{"auth": "secret123"}'
        """
        if not isinstance(text, str):
            return text

        # Find all ${VAR_NAME} patterns
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, text)

        # Replace each match with its environment value
        result = text
        for var_name in matches:
            var_value = os.getenv(var_name)
            if var_value is None:
                raise ConfigurationError(
                    f"Template variable ${{{var_name}}} referenced in ENDPOINTS but "
                    f"{var_name} is not defined in environment. Please add it to .env file."
                )
            result = result.replace(f"${{{var_name}}}", var_value)

        return result

    @staticmethod
    def has_template_vars(text: str) -> bool:
        """Check if text contains template variables."""
        if not isinstance(text, str):
            return False
        pattern = r"\$\{([^}]+)\}"
        return bool(re.search(pattern, text))


class EndpointsLoader:
    """Loads and validates endpoint configurations from environment.

    Follows Single Responsibility Principle - handles only endpoint loading.
    """

    @staticmethod
    def parse_curl_config(env_var_name: str) -> Optional[str]:
        """
        Parse a cURL-like endpoint configuration from an environment variable.

        The value can be a JSON string or a simple URL.
        Returns the parsed JSON object, raw string URL, or None if missing.

        Args:
            env_var_name: Name of environment variable to read

        Returns:
            Parsed configuration or None
        """
        value = os.getenv(env_var_name)
        if not value:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def load_from_env() -> List:
        """
        Load the `ENDPOINTS` variable from the environment and validate it.

        The `ENDPOINTS` value must be a JSON array. Raises ConfigurationError
        with a clear English message when validation fails.

        Supports template variable substitution using ${VAR_NAME} syntax to
        separate sensitive credentials from endpoint structure.

        Returns:
            List of endpoint configurations

        Raises:
            ConfigurationError: If ENDPOINTS is missing, invalid, or empty
        """
        endpoints_str = os.getenv("ENDPOINTS")

        if not endpoints_str:
            raise ConfigurationError(
                "ENDPOINTS environment variable is not set. Please configure a JSON array "
                "of endpoints in the .env file"
            )

        # Resolve template variables (${VAR_NAME}) before parsing JSON
        endpoints_str = TemplateResolver.resolve(endpoints_str)

        try:
            endpoints = json.loads(endpoints_str)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Error parsing ENDPOINTS: {exc}. It must be a valid JSON array"
            ) from exc

        if not isinstance(endpoints, list):
            raise ConfigurationError("ENDPOINTS must be a JSON array")

        if not endpoints:
            raise ConfigurationError("ENDPOINTS array cannot be empty")

        return endpoints

    @staticmethod
    def validate_endpoint(endpoint) -> bool:
        """
        Validate an endpoint configuration.

        Args:
            endpoint: Endpoint configuration (string URL or dict)

        Returns:
            True if valid, False otherwise
        """
        if isinstance(endpoint, str):
            return bool(endpoint.strip())
        if isinstance(endpoint, dict):
            return "url" in endpoint and bool(endpoint["url"])
        return False


# Backwards compatibility - expose functions at module level
def resolve_template_vars(text):
    """Legacy wrapper for TemplateResolver.resolve()."""
    return TemplateResolver.resolve(text)


def parse_curl_config(env_var_name):
    """Legacy wrapper for EndpointsLoader.parse_curl_config()."""
    return EndpointsLoader.parse_curl_config(env_var_name)


def load_endpoints_from_env():
    """Legacy wrapper for EndpointsLoader.load_from_env()."""
    return EndpointsLoader.load_from_env()
