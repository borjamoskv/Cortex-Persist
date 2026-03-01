"""CORTEX v5.0 — SAP OData Vault.

Handles HTTP Authentication (Basic/OAuth2) and CSRF token management.
"""

from __future__ import annotations

import httpx

from cortex.sap.models import SAPAuthError, SAPConfig

__all__ = ["SAPVault"]


class SAPVault:
    """Manages credentials, sessions, and CSRF tokens for SAP."""

    def __init__(self, config: SAPConfig) -> None:
        self.config = config
        self._csrf_token: str | None = None
        self._oauth_token: str | None = None

    @property
    def has_csrf(self) -> bool:
        """Return True if a CSRF token is currently held."""
        return bool(self._csrf_token)

    def set_csrf_token(self, token: str) -> None:
        """Store a newly fetched CSRF token."""
        self._csrf_token = token

    def clear(self) -> None:
        """Clear all stored session tokens."""
        self._csrf_token = None
        self._oauth_token = None

    async def get_auth_headers(self, client: httpx.AsyncClient) -> dict[str, str]:
        """Build and return authentication headers.

        Args:
            client: Active httpx.AsyncClient used to fetch OAuth tokens if needed.
        """
        headers: dict[str, str] = {}

        if self.config.client:
            headers["sap-client"] = self.config.client

        if self.config.auth_type == "basic":
            import base64

            creds = base64.b64encode(
                f"{self.config.username}:{self.config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

        elif self.config.auth_type == "oauth2":
            token = await self._fetch_oauth_token(client)
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def build_request_headers(
        self, method: str, auth_headers: dict[str, str], has_json: bool
    ) -> dict[str, str]:
        """Combine auth, config, CSRF, and content-type headers into a request payload."""
        headers = {
            **auth_headers,
            **self.config.headers,
            "Accept": "application/json",
        }

        # Add CSRF for write operations
        if method in {"POST", "PUT", "PATCH", "DELETE"} and self._csrf_token:
            headers["x-csrf-token"] = self._csrf_token

        if has_json:
            headers["Content-Type"] = "application/json"

        return headers

    async def _fetch_oauth_token(self, client: httpx.AsyncClient) -> str:
        """Obtain OAuth2 token via client credentials grant."""
        if self._oauth_token:
            return self._oauth_token

        try:
            resp = await client.post(
                self.config.oauth_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.oauth_client_id,
                    "client_secret": self.config.oauth_client_secret,
                },
            )
        except httpx.ConnectError as e:
            raise SAPAuthError(f"OAuth2 connect error: {e}") from e

        if resp.status_code != 200:
            raise SAPAuthError(f"OAuth2 token request failed: {resp.status_code}")

        self._oauth_token = resp.json().get("access_token", "")
        return self._oauth_token
