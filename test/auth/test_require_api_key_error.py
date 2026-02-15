
"""Tests for require_api_key error handling."""

from flask import Flask
from src.auth import require_api_key

def test_require_api_key_error_response():
    """Test require_api_key error response when header is missing."""
    app = Flask(__name__)
    app.config["TESTING"] = False
    app.config["API_KEY"] = "secret-key"
    @app.route("/protected")
    @require_api_key()
    def protected():
        return "should not get here"
    with app.test_client() as client:
        # No API key header
        resp = client.get("/protected")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "Missing X-API-Key header"
        assert "requires authentication" in data["message"]
        # Wrong API key
        resp = client.get("/protected", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"] == "Invalid X-API-Key"
        assert "not valid" in data["message"]
