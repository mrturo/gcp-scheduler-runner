"""
Tests for src/config.py configuration and parsing.
"""

import os
import sys

import pytest
from unittest.mock import patch
from src.config import load_endpoints_from_env, parse_curl_config

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

@patch("os.getenv")
def test_parse_curl_config_with_json(mock_getenv):
    """
    Test parse_curl_config parses JSON string correctly.
    """
    mock_getenv.return_value = '{"url": "http://example.com"}'
    result = parse_curl_config("TEST_VAR")
    assert result == {"url": "http://example.com"}

@patch("os.getenv")
def test_parse_curl_config_with_url(mock_getenv):
    """
    Test parse_curl_config returns URL string as is.
    """
    mock_getenv.return_value = "http://example.com"
    result = parse_curl_config("TEST_VAR")
    assert result == "http://example.com"

@patch("os.getenv")
def test_parse_curl_config_not_found(mock_getenv):
    """
    Test parse_curl_config returns None if variable not found.
    """
    mock_getenv.return_value = None
    result = parse_curl_config("TEST_VAR")
    assert result is None

@patch("os.getenv")
def test_load_endpoints_from_env_success(mock_getenv):
    """
    Test load_endpoints_from_env parses valid JSON array.
    """
    mock_getenv.return_value = '[{"url": "http://example.com"}]'
    result = load_endpoints_from_env()
    assert len(result) == 1
    assert result[0]["url"] == "http://example.com"

@patch("os.getenv")
def test_load_endpoints_from_env_missing_var(mock_getenv):
    """
    Test load_endpoints_from_env raises error if variable missing.
    """
    mock_getenv.return_value = None
    from src.config import ConfigurationError
    with pytest.raises(ConfigurationError, match="ENDPOINTS environment variable is not set"):
        load_endpoints_from_env()

@patch("os.getenv")
def test_load_endpoints_from_env_invalid_json(mock_getenv):
    """
    Test load_endpoints_from_env raises error on invalid JSON.
    """
    mock_getenv.return_value = "not valid json"
    from src.config import ConfigurationError
    with pytest.raises(ConfigurationError, match="Error parsing ENDPOINTS"):
        load_endpoints_from_env()

@patch("os.getenv")
def test_load_endpoints_from_env_not_list(mock_getenv):
    """
    Test load_endpoints_from_env raises error if not a list.
    """
    mock_getenv.return_value = '{"url": "http://example.com"}'
    from src.config import ConfigurationError
    with pytest.raises(ConfigurationError, match="ENDPOINTS must be a JSON array"):
        load_endpoints_from_env()

@patch("os.getenv")
def test_load_endpoints_from_env_empty_list(mock_getenv):
    """
    Test load_endpoints_from_env raises error if array is empty.
    """
    mock_getenv.return_value = "[]"
    from src.config import ConfigurationError
    with pytest.raises(ConfigurationError, match="ENDPOINTS array cannot be empty"):
        load_endpoints_from_env()
