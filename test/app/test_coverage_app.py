"""
Coverage tests for src/app.py (errors and exceptions).
"""

import os
import sys
import types
from unittest.mock import patch

import pytest
from src import app as app_module

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_index_endpoint_exception(monkeypatch):
    """
    Test index endpoint exception handling when endpoints cannot be loaded.
    """
    monkeypatch.setattr(app_module, "ENDPOINTS_TO_EXECUTE", None)
    monkeypatch.setattr(app_module, "load_endpoints_from_env", lambda: (_ for _ in ()).throw(ValueError("fail")))
    monkeypatch.setattr(app_module, "require_api_key", lambda f: f)
    client = app_module.app.test_client()
    resp = client.get("/", headers={"X-API-Key": "test-api-key-123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["configured_endpoints"] == 0

def test_execute_endpoints_get_exception(monkeypatch):
    """
    Test /execute endpoint exception handling when endpoints cannot be loaded.
    """
    monkeypatch.setattr(app_module, "ENDPOINTS_TO_EXECUTE", None)
    monkeypatch.setattr(app_module, "load_endpoints_from_env", lambda: (_ for _ in ()).throw(ValueError("fail")))
    monkeypatch.setattr(app_module, "require_api_key", lambda f: f)
    client = app_module.app.test_client()
    resp = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_endpoints"] == 0

def test_execute_endpoints_get_executor_exception(monkeypatch):
    """
    Test /execute endpoint error handling when HTTPExecutor fails.
    """
    monkeypatch.setattr(app_module, "ENDPOINTS_TO_EXECUTE", ["http://mocked"])
    class DummyExecutor:
        def __init__(self, *a, **k):
            pass
        def execute(self, *a, **k):
            raise RuntimeError("fail-execute")
        def public_method(self):
            return True
        def second_public_method(self):
            return True
    monkeypatch.setattr(app_module, "require_api_key", lambda f: f)
    monkeypatch.setattr(app_module, "HTTPExecutor", DummyExecutor)
    client = app_module.app.test_client()
    resp = client.get("/execute", headers={"X-API-Key": "test-api-key-123"})
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["success"] is False
    assert "fail-execute" in str(data["details"]["errors"][0])

def test_get_configured_endpoints_count_exception(monkeypatch):
    """
    Test _get_configured_endpoints_count returns 0 on exception.
    """
    monkeypatch.setattr(app_module, "ENDPOINTS_TO_EXECUTE", None)
    monkeypatch.setattr(app_module, "load_endpoints_from_env", lambda: (_ for _ in ()).throw(ValueError("fail")))
    assert getattr(app_module, "_get_configured_endpoints_count")() == 0

def test_handle_email_notification_disabled(capsys):
    """
    Test _handle_email_notification outputs DISABLED and sets email_sent False.
    """
    summary = types.SimpleNamespace()
    summary.email_notification = None
    getattr(app_module, "_handle_email_notification")(False, summary)
    out = capsys.readouterr().out
    assert "DISABLED" in out
    assert summary.email_notification["email_sent"] is False
