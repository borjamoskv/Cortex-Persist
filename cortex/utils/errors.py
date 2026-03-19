"""
CORTEX v5.0 — Custom Exceptions.

Typed error hierarchy to avoid leaking internal DB details
through API boundaries (Sprint 0 security directive).
"""

from __future__ import annotations

__all__ = [
    "CortexError",
    "DBLockError",
    "FactNotFound",
    # KETER-∞ Phase 1
    "AuthError",
    "PermissionDeniedError",
    "SovereignViolation",
]


class CortexError(Exception):
    """Base exception for all CORTEX errors."""


class DBLockError(CortexError):
    """Raised when an operation fails due to SQLite locking after timeout."""


class FactNotFound(CortexError):
    """Raised when a fact is not found."""


class AuthError(CortexError):
    """Base exception for auth-related failures."""

    pass


class PermissionDeniedError(AuthError):
    """Raised when an operation is rejected by RBAC."""

    pass


class SovereignViolation(CortexError):
    """Raised when a sovereign policy is violated (e.g., Rule 1.3 model tier)."""

    pass
