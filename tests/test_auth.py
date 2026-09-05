"""Unit tests for auth.py."""

import pytest
from auth import AuthManager


def test_auth_manager_defaults():
    """Test AuthManager initializes with default mock values if env is unset."""
    auth = AuthManager()
    assert auth.is_authenticated() is True
    headers = auth.get_headers()
    assert "Authorization" in headers
    assert "X-API-Key" in headers
    assert headers["Content-Type"] == "application/json"


def test_auth_manager_custom_credentials():
    """Test AuthManager with custom credentials."""
    auth = AuthManager(api_key="custom_key", token="custom_token")
    assert auth.is_authenticated() is True
    headers = auth.get_headers()
    assert headers["X-API-Key"] == "custom_key"
    assert headers["Authorization"] == "Bearer custom_token"


def test_auth_manager_missing_credentials():
    """Test AuthManager error handling when credentials are missing."""
    auth = AuthManager(api_key="", token="")
    assert auth.is_authenticated() is False
    with pytest.raises(ValueError, match="Authentication credentials are missing or invalid"):
        auth.get_headers()
