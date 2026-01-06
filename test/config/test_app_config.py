"""
Tests for src/config.py configuration parsing functions.
"""

from unittest.mock import patch

from src.config import parse_curl_config

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
