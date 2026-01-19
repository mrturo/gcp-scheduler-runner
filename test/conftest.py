"""Pytest configuration and fixtures for test suite."""

import json

import pytest
from flask.testing import FlaskClient

import src.app as app_mod


# Fixture required by pytest-flask to provide the Flask app
@pytest.fixture
def app():
    """Fixture that returns the Flask app instance for pytest-flask."""
    app_mod.app.config.update({"TESTING": True})
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
