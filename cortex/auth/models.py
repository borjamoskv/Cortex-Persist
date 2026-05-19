"""CORTEX Auth — Data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from cortex.auth.rbac import Permission


@dataclass
class APIKey:
    """Represents an API key with its metadata."""

    id: int | str
    name: str
    key_prefix: str
    tenant_id: str
    role: str
    permissions: list[str]
    created_at: str
    last_used: str | None
    is_active: bool
    rate_limit: int


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    authenticated: bool
    tenant_id: str = "default"
    role: str = "user"
    permissions: list[str | Permission] = field(default_factory=list)
    key_name: str = ""
    error: str = ""
