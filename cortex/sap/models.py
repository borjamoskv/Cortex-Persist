"""CORTEX v5.0 — SAP OData Models & Exceptions.

Extracted from client.py to keep file size under 300 LOC.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "SAPAuthError",
    "SAPConfig",
    "SAPConnectionError",
    "SAPEntityError",
]


# ─── Exceptions ──────────────────────────────────────────────────────


class SAPConnectionError(Exception):
    """Failed to connect to SAP system."""


class SAPAuthError(Exception):
    """SAP authentication failed."""


class SAPEntityError(Exception):
    """SAP entity operation failed."""


# ─── Configuration ───────────────────────────────────────────────────


@dataclass
class SAPConfig:
    """SAP OData connection configuration."""

    base_url: str
    auth_type: str = "basic"
    username: str = ""
    password: str = ""
    client: str = ""
    oauth_token_url: str = ""
    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    timeout: int = 30
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def base_url_normalized(self) -> str:
        """Return base URL without trailing slash."""
        return self.base_url.rstrip("/")
