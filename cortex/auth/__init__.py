"""CORTEX v5.0 — Authentication & Authorization.

API key management with SHA-256 hashing. Keys are stored hashed,
never in plaintext. Supports scoped permissions per tenant.

This module re-exports from the decomposed submodules for backward
compatibility.  New code should import from submodules directly.
"""

from cortex.auth.deps import (
    require_auth,
    require_consensus,
    require_permission,
    require_verified_permission,
)
from cortex.auth.manager import AuthManager, get_auth_manager, reset_auth_manager
from cortex.auth.models import APIKey, AuthResult
from cortex.auth.schema import AUTH_SCHEMA, SQL_INSERT_KEY

__all__ = [
    "APIKey",
    "AUTH_SCHEMA",
    "AuthManager",
    "AuthResult",
    "SQL_INSERT_KEY",
    "get_auth_manager",
    "require_auth",
    "require_consensus",
    "require_permission",
    "require_verified_permission",
    "reset_auth_manager",
]
