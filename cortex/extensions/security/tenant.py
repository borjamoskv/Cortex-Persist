"""CORTEX v5.2 — Tenancy Context (RLS Support).

Stores and retrieves the tenant ID context dynamically for Row Level Security (RLS)
isolation in the database engine without explicitly passing it down all call chains.
"""

import contextvars
import os


class TenantContextMissingError(RuntimeError):
    """Raised when tenant context is required but missing."""


tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id")


def _legacy_default_tenant_enabled() -> bool:
    """Enable transitional default tenant fallback only when explicitly requested."""
    return os.getenv("CORTEX_ALLOW_LEGACY_DEFAULT_TENANT", "").lower() in {"1", "true", "yes"}


def get_tenant_id() -> str:
    """Retrieve current tenant context, failing closed when no context exists."""
    try:
        return tenant_id_var.get()
    except LookupError as exc:
        if _legacy_default_tenant_enabled():
            return "default"
        raise TenantContextMissingError(
            "Missing tenant context; tenant_id must be explicitly bound before access."
        ) from exc
