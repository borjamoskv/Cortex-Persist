"""
CORTEX v5.0 — Custom Exceptions.

Typed error hierarchy to avoid leaking internal DB details
through API boundaries (Sprint 0 security directive).
"""

__all__ = [
    "CortexError",
    "CriticalSubsystemError",
    "CortexDatabaseError",
    "DatabaseTransactionError",
    "ConnectionPoolExhausted",
    "DBLockError",
    "FactNotFound",
    "ProjectNotFound",
    "ThreadPoolExhausted",
    # KETER-∞ Phase 1
    "LLMRoutingError",
    "LLMProviderError",
    "MemorySubsystemError",
    "ValidationBoundaryError",
    "ConsensusFailure",
    "WriteWorkerError",
    "AuthError",
    "PermissionDeniedError",
]


class CortexError(Exception):
    """Base exception for all CORTEX errors."""


class CriticalSubsystemError(CortexError):
    """Raised when a core subsystem fails unexpectedly."""


class CortexDatabaseError(CriticalSubsystemError):
    """Base exception for all database-related sovereign errors."""


class ConnectionPoolExhausted(CortexDatabaseError):
    """Raised when the SQLite connection pool is exhausted."""


class DBLockError(CortexDatabaseError):
    """Raised when an operation fails due to SQLite locking after timeout."""


class DatabaseTransactionError(CortexError):
    """Raised when a database transaction fails and has been rolled back.

    This exception sanitizes internal SQLite error details so they are
    never exposed to external callers or API consumers.
    """


class FactNotFound(CortexError):
    """Raised when a fact is not found."""


class ProjectNotFound(CortexError):
    """Raised when a project is not found."""


class ThreadPoolExhausted(CortexError):
    """Raised when thread pool is saturated."""


class MemorySubsystemError(CortexError):
    """Raised when the cognitive memory subsystem fails."""


# ─── KETER-∞ Phase 1: Extended Hierarchy ─────────────────────────────


class LLMRoutingError(CriticalSubsystemError):
    """Raised when all LLM providers fail (Singularidad Negativa)."""


class LLMProviderError(CortexError):
    """Raised when a single LLM provider fails (non-critical, triggers fallback)."""


class ValidationBoundaryError(CortexError):
    """Raised when Pydantic perimeter validation fails on LLM output.

    Carries structured error info for automated retry/correction loops.
    """

    def __init__(self, message: str, validation_errors: list[dict] | None = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class ConsensusFailure(CriticalSubsystemError):
    """Raised when the agent swarm cannot reach quorum."""


class WriteWorkerError(CortexDatabaseError):
    """Raised when the SqliteWriteWorker fails to process an operation."""


class AuthError(CortexError):
    """Base exception for auth-related failures."""

    pass


class PermissionDeniedError(AuthError):
    """Raised when an operation is rejected by RBAC."""

    pass
