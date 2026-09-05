"""Authentication module for data pipeline.

Handles API token validation, environment variable configuration,
and request header generation.
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class AuthManager:
    """Manages API authentication credentials and request headers."""

    def __init__(self, api_key: Optional[str] = None, token: Optional[str] = None):
        """Initialize AuthManager with optional explicit credentials or from environment."""
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("API_KEY", "mock-default-api-key")

        if token is not None:
            self.token = token
        else:
            self.token = os.getenv("AUTH_TOKEN", "mock-bearer-token")

    def is_authenticated(self) -> bool:
        """Check whether valid credentials exist."""
        return bool(self.api_key and self.token)

    def get_headers(self) -> Dict[str, str]:
        """Return standardized authorization headers for API requests."""
        if not self.is_authenticated():
            raise ValueError("Authentication credentials are missing or invalid.")

        return {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityDataPipeline/1.0",
        }
