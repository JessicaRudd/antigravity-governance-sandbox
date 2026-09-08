"""Authentication module for data pipeline.

Handles API token validation, environment variable configuration,
and request header generation.
"""

import datetime
import os
import time
from typing import Any, Callable, Dict, Optional, Union
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class TokenExpiredError(ValueError):
    """Raised when an authentication token has expired."""

    pass


class RefreshTokenStr(str):
    """String subclass representing a refresh token that can also be called as a refresh hook."""

    def __new__(cls, value: str, manager: Optional["AuthManager"] = None):
        """Create a new RefreshTokenStr instance."""
        instance = super().__new__(cls, value)
        instance._manager = manager
        return instance

    def __call__(
        self,
        new_token: Optional[str] = None,
        expires_at: Optional[Union[float, int, datetime.datetime, str]] = None,
    ) -> bool:
        """Invoke refresh credentials on the associated AuthManager."""
        if self._manager is not None:
            return self._manager.refresh_credentials(new_token=new_token, expires_at=expires_at)
        return False


class AuthManager:
    """Manages API authentication credentials and request headers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        expires_at: Optional[Union[float, int, datetime.datetime, str]] = None,
        refresh_token: Optional[Union[str, Callable[..., Any]]] = None,
        refresh_callback: Optional[Callable[..., Any]] = None,
    ):
        """Initialize AuthManager with optional explicit credentials or from environment."""
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("API_KEY", "mock-default-api-key")

        if token is not None:
            self.token = token
        else:
            self.token = os.getenv("AUTH_TOKEN", "mock-bearer-token")

        if expires_at is not None:
            self.expires_at = expires_at
        else:
            env_exp = os.getenv("AUTH_EXPIRES_AT")
            self.expires_at = float(env_exp) if env_exp else None

        self.refresh_callback = refresh_callback
        if callable(refresh_token) and not isinstance(refresh_token, str):
            self.refresh_callback = refresh_token
            self.refresh_token = None
        elif refresh_token is not None:
            self.refresh_token = RefreshTokenStr(str(refresh_token), manager=self)
        else:
            env_refresh = os.getenv("REFRESH_TOKEN")
            self.refresh_token = RefreshTokenStr(env_refresh, manager=self) if env_refresh else None

    def is_token_expired(self) -> bool:
        """Check whether the current token has expired."""
        if self.expires_at is None:
            return False

        if isinstance(self.expires_at, datetime.datetime):
            if self.expires_at.tzinfo is None:
                now = datetime.datetime.now()
            else:
                now = datetime.datetime.now(datetime.timezone.utc)
            return now >= self.expires_at

        if isinstance(self.expires_at, str):
            try:
                exp_float = float(self.expires_at)
                return time.time() >= exp_float
            except ValueError:
                dt = datetime.datetime.fromisoformat(self.expires_at)
                now = datetime.datetime.now(datetime.timezone.utc) if dt.tzinfo else datetime.datetime.now()
                return now >= dt

        return time.time() >= float(self.expires_at)

    def is_authenticated(self) -> bool:
        """Check whether valid credentials exist and the token is not expired."""
        return bool(self.api_key and self.token and not self.is_token_expired())

    def refresh_credentials(
        self,
        new_token: Optional[str] = None,
        expires_at: Optional[Union[float, int, datetime.datetime, str]] = None,
    ) -> bool:
        """Refresh credentials via provided token, callback, or refresh token."""
        if new_token is not None:
            self.token = new_token
            self.expires_at = expires_at
            return True

        if self.refresh_callback is not None:
            res = self.refresh_callback(self)
            if isinstance(res, tuple) and len(res) == 2:
                self.token, self.expires_at = res
            elif isinstance(res, str):
                self.token = res
                self.expires_at = expires_at
            return True

        if self.refresh_token:
            self.token = f"refreshed-{self.refresh_token}"
            self.expires_at = expires_at
            return True

        return False

    def refresh_token_hook(
        self,
        new_token: Optional[str] = None,
        expires_at: Optional[Union[float, int, datetime.datetime, str]] = None,
    ) -> bool:
        """Hook to refresh the current token."""
        return self.refresh_credentials(new_token=new_token, expires_at=expires_at)

    def get_headers(self) -> Dict[str, str]:
        """Return standardized authorization headers for API requests."""
        if not (self.api_key and self.token):
            raise ValueError("Authentication credentials are missing or invalid.")

        if self.is_token_expired():
            # Attempt refresh if a callback or refresh token is available
            refreshed = False
            if self.refresh_callback is not None or self.refresh_token is not None:
                try:
                    refreshed = self.refresh_credentials()
                except Exception as err:
                    raise ValueError(f"Authentication token expired and refresh failed: {err}") from err

            if not refreshed or self.is_token_expired():
                raise TokenExpiredError(
                    "Authentication token has expired. Please refresh the token or provide valid credentials."
                )

        return {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityDataPipeline/1.0",
        }
