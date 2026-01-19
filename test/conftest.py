"""Pytest configuration and fixtures for test suite."""

import json

import pytest
from flask.testing import FlaskClient

import src.app as app_mod


# Fixture requerido por pytest-flask para proveer la app de Flask
@pytest.fixture
def app():
    """Fixture que retorna la instancia de Flask app para pytest-flask."""
    app_mod.app.config.update({"TESTING": True})
    return app_mod.app


@pytest.fixture(autouse=True)
def force_test_mode_in_execute_requests(monkeypatch):
    """
    Fuerza que todos los requests POST a /execute incluyan test_mode=True en el body,
    si no está presente. Esto asegura que el asunto del correo sea siempre 'Test Execution Report'.
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
