"""
Coverage tests for src/config.py (AppConfig, ServerConfig, TemplateResolver, EndpointsLoader).
"""

import os
import sys

from datetime import datetime

import pytest
from src.config import (
    AppConfig,
    ServerConfig,
    EmailConfig,
    EndpointsLoader,
    TemplateResolver,
    resolve_template_vars,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_server_config_get_port(monkeypatch):
    """
    Test ServerConfig.get_port returns correct port from environment.
    """
    monkeypatch.setenv("PORT", "8080")
    config = ServerConfig()
    assert config.get_port() == 8080

def test_server_config_has_api_key_true(monkeypatch):
    """
    Test ServerConfig.has_api_key returns True when API_KEY is set.
    """
    monkeypatch.setenv("API_KEY", "test_key_123")
    config = ServerConfig()
    assert config.has_api_key() is True

def test_server_config_has_api_key_false(monkeypatch):
    """
    Test ServerConfig.has_api_key returns False when API_KEY is not set.
    """
    monkeypatch.delenv("API_KEY", raising=False)
    config = ServerConfig()
    assert config.has_api_key() is False

def test_email_config_get_smtp_config(monkeypatch):
    """
    Test EmailConfig.get_smtp_config returns correct SMTP config.
    """
    monkeypatch.setenv("EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password123")
    config = EmailConfig()
    smtp_config = config.get_smtp_config()
    assert smtp_config["host"] == "smtp.gmail.com"
    assert smtp_config["port"] == 587

def test_app_config_singleton_initialized_flag(monkeypatch):
    """
    Test AppConfig singleton initialization and instance reuse.
    """
    original_instance = getattr(AppConfig, "_instance")
    original_initialized = getattr(AppConfig, "_initialized")
    setattr(AppConfig, "_instance", None)
    setattr(AppConfig, "_initialized", False)
    monkeypatch.setenv("PORT", "3000")
    monkeypatch.setenv("API_KEY", "test_key")
    try:
        config1 = AppConfig()
        assert config1 is not None
        assert hasattr(config1, "server")
        assert hasattr(config1, "email")
        assert getattr(config1, "_initialized") is True
        config2 = AppConfig()
        assert config1 is config2
    finally:
        setattr(AppConfig, "_instance", original_instance)
        setattr(AppConfig, "_initialized", original_initialized)

def test_app_config_is_email_configured(monkeypatch):
    """
    Test AppConfig.is_email_configured returns True when email is configured.
    """
    monkeypatch.setenv("EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    setattr(AppConfig, "_instance", None)
    config = AppConfig()
    assert config.is_email_configured is True

def test_template_resolver_has_template_vars_with_non_string():
    """
    Test TemplateResolver.has_template_vars returns False for non-string inputs.
    """
    assert TemplateResolver.has_template_vars(12345) is False
    assert TemplateResolver.has_template_vars(None) is False
    assert TemplateResolver.has_template_vars([]) is False

def test_template_resolver_has_template_vars_with_templates():
    """
    Test TemplateResolver.has_template_vars detects template variables.
    """
    assert TemplateResolver.has_template_vars("${VAR}") is True
    assert TemplateResolver.has_template_vars("no templates") is False

def test_endpoints_loader_validate_endpoint():
    """
    Test EndpointsLoader.validate_endpoint for various input types.
    """
    assert EndpointsLoader.validate_endpoint("http://example.com") is True
    assert EndpointsLoader.validate_endpoint("   ") is False
    assert EndpointsLoader.validate_endpoint({"url": "http://example.com"}) is True
    assert EndpointsLoader.validate_endpoint({"method": "POST"}) is False
    assert EndpointsLoader.validate_endpoint(12345) is False

def test_resolve_template_vars_legacy_wrapper():
    """
    Test resolve_template_vars legacy wrapper returns input if no templates.
    """
    result = resolve_template_vars("No templates here")
    assert result == "No templates here"
