"""Pytest configuration and fixtures for test suite."""

import json
import os

import pytest
from flask.testing import FlaskClient

# Keep local developer secrets and live endpoint configuration out of tests.
# This must be set before importing src.config, which loads dotenv at import time.
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "true")
os.environ.setdefault("API_KEY", "test-api-key-123")

import src.app as app_mod  # noqa: E402


# Fixture required by pytest-flask to provide the Flask app
@pytest.fixture(autouse=True)
def prevent_external_smtp(monkeypatch):
    """Keep application tests from opening real SMTP connections."""

    class DummySMTP:
        """Minimal SMTP context manager for deterministic tests."""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            return None

    monkeypatch.setattr("smtplib.SMTP", DummySMTP)


@pytest.fixture
def app():
    """Fixture that returns the Flask app instance for pytest-flask."""
    app_mod.app.config.update({"TESTING": True})
    app_mod.config.email.smtp_user = "test@example.com"
    app_mod.config.email.smtp_password = "password123"
    app_mod.config.email.email_from = "test@example.com"
    app_mod.config.email.email_to = "recipient@example.com"
    return app_mod.app


@pytest.fixture(autouse=True)
def force_test_mode_in_execute_requests(monkeypatch):
    """
    Forces all POST requests to /execute to include test_mode=True in the body if not present.
    This ensures the email subject is always 'Test Execution Report'.
    """
    original_post = FlaskClient.post

    def custom_post(self, *args, **kwargs):
        if args and "/execute" in args[0]:
            data = kwargs.get("data")
            content_type = kwargs.get("content_type", "")
            if data and "json" in content_type:
                try:
                    payload = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return original_post(self, *args, **kwargs)
                if "test_mode" not in payload:
                    payload["test_mode"] = True
                    kwargs["data"] = json.dumps(payload)
        return original_post(self, *args, **kwargs)

    monkeypatch.setattr(FlaskClient, "post", custom_post)
