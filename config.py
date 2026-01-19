"""Configuration utilities for loading endpoints and settings from environment.

This module exposes helper functions that parse endpoint configuration from
environment variables. Endpoint loading is performed on demand (not at import
time) to make the module easier to test.

Supports template variable substitution in ENDPOINTS using ${VAR_NAME} syntax.
This allows separating sensitive credentials from endpoint structure.
"""

import json
import os
import re

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Port configuration
PORT = int(os.getenv("PORT", "3000"))

# API Key for authentication (optional)
API_KEY = os.getenv("API_KEY")


def resolve_template_vars(text):
    """Resolve template variables in text using ${VAR_NAME} syntax.

    Replaces all occurrences of ${VARIABLE_NAME} with the value from environment.
    Raises ValueError if a referenced variable is not defined.

    Args:
        text: String containing template variables (e.g., '{"key": "${SECRET}"}')

    Returns:
        String with all template variables replaced with their values

    Example:
        >>> os.environ['TOKEN'] = 'secret123'
        >>> resolve_template_vars('{"auth": "${TOKEN}"}')
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
            raise ValueError(
                f"Template variable ${{{var_name}}} referenced in ENDPOINTS but "
                f"{var_name} is not defined in environment. Please add it to .env file."
            )
        result = result.replace(f"${{{var_name}}}", var_value)

    return result


def parse_curl_config(env_var_name):
    """Parse a cURL-like endpoint configuration from an environment variable.

    The value can be a JSON string describing the endpoint, or a simple URL.
    Returns the parsed JSON object or the raw string URL, or None if missing.
    """
    value = os.getenv(env_var_name)
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_endpoints_from_env():
    """Load the `ENDPOINTS` variable from the environment and validate it.

    The `ENDPOINTS` value must be a JSON array. Raises ValueError with a clear
    English message when validation fails.

    Supports template variable substitution using ${VAR_NAME} syntax to separate
    sensitive credentials from endpoint structure.
    """
    endpoints_str = os.getenv("ENDPOINTS")

    if not endpoints_str:
        raise ValueError(
            "ENDPOINTS environment variable is not set. Please configure a JSON array "
            "of endpoints in the .env file"
        )

    # Resolve template variables (${VAR_NAME}) before parsing JSON
    endpoints_str = resolve_template_vars(endpoints_str)

    try:
        endpoints = json.loads(endpoints_str)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Error parsing ENDPOINTS: {e}. It must be a valid JSON array"
        ) from e

    if not isinstance(endpoints, list):
        raise ValueError("ENDPOINTS must be a JSON array")

    if not endpoints:
        raise ValueError("ENDPOINTS array cannot be empty")

    return endpoints


# Request timeout (seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
