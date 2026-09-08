"""Unit tests for auth.py."""

import datetime
import time
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


def test_auth_manager_valid_unexpired_token():
    """Test AuthManager with an active, unexpired token."""
    future_time = time.time() + 3600
    auth = AuthManager(api_key="k", token="t", expires_at=future_time)
    assert auth.is_token_expired() is False
    assert auth.is_authenticated() is True
    headers = auth.get_headers()
    assert headers["Authorization"] == "Bearer t"


def test_auth_manager_expired_token_raises():
    """Test AuthManager raises TokenExpiredError when token is expired."""
    past_time = time.time() - 100
    auth = AuthManager(api_key="k", token="t", expires_at=past_time)
    assert auth.is_token_expired() is True
    assert auth.is_authenticated() is False
    with pytest.raises(ValueError, match="Authentication token has expired"):
        auth.get_headers()


def test_auth_manager_datetime_expiration():
    """Test token expiration handling with datetime objects."""
    future_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    past_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)

    auth_valid = AuthManager(expires_at=future_dt)
    assert auth_valid.is_token_expired() is False

    auth_expired = AuthManager(expires_at=past_dt)
    assert auth_expired.is_token_expired() is True


def test_auth_manager_refresh_token_attribute():
    """Test refresh_token attribute access and representation."""
    auth = AuthManager(api_key="k", token="t", refresh_token="sample_refresh_token")
    assert auth.refresh_token == "sample_refresh_token"
    assert isinstance(auth.refresh_token, str)


def test_auth_manager_auto_refresh_on_get_headers():
    """Test AuthManager automatically refreshes expired token during get_headers."""
    past_time = time.time() - 50

    def mock_refresh(manager):
        manager.token = "renewed_token"
        manager.expires_at = time.time() + 3600
        return True

    auth = AuthManager(
        api_key="k",
        token="expired_token",
        expires_at=past_time,
        refresh_callback=mock_refresh,
    )
    assert auth.is_token_expired() is True
    headers = auth.get_headers()
    assert headers["Authorization"] == "Bearer renewed_token"
    assert auth.is_token_expired() is False


def test_auth_manager_refresh_failure_raises():
    """Test AuthManager raises error when refresh callback raises an exception."""
    past_time = time.time() - 50

    def failing_refresh(manager):
        raise RuntimeError("Network failure during token refresh")

    auth = AuthManager(
        api_key="k",
        token="expired_token",
        expires_at=past_time,
        refresh_callback=failing_refresh,
    )
    with pytest.raises(ValueError, match="Authentication token expired and refresh failed"):
        auth.get_headers()
