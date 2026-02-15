
"""Tests for require_api_key auth error handling."""

from flask import Flask
from src.auth import require_api_key, AuthenticationError

def test_require_api_key_authenticationerror_branch(monkeypatch):
    """Test require_api_key branch that raises AuthenticationError."""
    app = Flask(__name__)
    app.config["TESTING"] = False
    app.config["API_KEY"] = "secret-key"
    # Patch APIKeyAuthenticator to always raise AuthenticationError
    # Import inside function to avoid import-outside-toplevel warning
    import src.auth as auth_module  # pylint: disable=import-outside-toplevel  # Required for patching in test context
    class DummyAuth:
        """Dummy authenticator that always raises AuthenticationError."""
        def __init__(self, key):
            self.key = key
        def validate(self, provided_key):
            """Always raise AuthenticationError for testing."""
            raise AuthenticationError("Unit test error", 418)
        def get_key(self):
            """Return the stored key (dummy method for pylint compliance)."""
            return self.key
    monkeypatch.setattr(auth_module, "APIKeyAuthenticator", DummyAuth)
    @app.route("/protected")
    @require_api_key()
    def protected():
        """Protected endpoint for testing."""
        return "should not get here"
    with app.test_client() as client:
        resp = client.get("/protected", headers={"X-API-Key": "secret-key"})
        assert resp.status_code == 418
        data = resp.get_json()
        assert data["error"] == "Unit test error"
        assert data["message"] == "Unit test error"
