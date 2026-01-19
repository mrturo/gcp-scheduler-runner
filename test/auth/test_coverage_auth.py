"""
Coverage tests for src/auth.py (APIKeyAuthenticator and decorator).
"""

import os
import sys

from flask import Flask, jsonify
import pytest
from src.auth import APIKeyAuthenticator, AuthenticationError, require_api_key

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_apikeyauthenticator_validate_missing_key():
    """
    Test APIKeyAuthenticator.validate raises 401 if key is missing.
    """
    auth = APIKeyAuthenticator("abc123")
    auth.is_enabled = True
    try:
        auth.validate(None)
    except AuthenticationError as exc:
        assert exc.status_code == 401
        assert "Missing X-API-Key" in exc.message
    else:
        assert False, "AuthenticationError not raised"

def test_apikeyauthenticator_validate_invalid_key():
    """
    Test APIKeyAuthenticator.validate raises 403 if key is invalid.
    """
    auth = APIKeyAuthenticator("abc123")
    auth.is_enabled = True
    try:
        auth.validate("wrong")
    except AuthenticationError as exc:
        assert exc.status_code == 403
        assert "Invalid X-API-Key" in exc.message
    else:
        assert False, "AuthenticationError not raised"

def test_apikeyauthenticator_validate_disabled():
    """
    Test APIKeyAuthenticator.validate does not raise if disabled.
    """
    auth = APIKeyAuthenticator("abc123")
    auth.is_enabled = False
    auth.validate(None)
    auth.validate("wrong")

def test_apikeyauthenticator_is_authentication_enabled():
    """
    Test APIKeyAuthenticator.is_authentication_enabled and require_api_key decorator.
    """
    auth = APIKeyAuthenticator("abc123")
    assert auth.is_authentication_enabled() is True
    auth.is_enabled = False
    assert auth.is_authentication_enabled() is False
    app = Flask(__name__)
    app.config["TESTING"] = True
    @app.route("/test")
    @require_api_key()
    def test_route():
        return jsonify({"ok": True})
    with app.test_client() as client:
        resp = client.get("/test", headers={"X-API-Key": "test-api-key-123"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
