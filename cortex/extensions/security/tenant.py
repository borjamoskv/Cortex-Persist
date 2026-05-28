"""CORTEX v5.2 — Tenancy Context (RLS Support).

Stores and retrieves the tenant ID context dynamically for Row Level Security (RLS)
isolation in the database engine without explicitly passing it down all call chains.
"""

import contextvars
import os

tenant_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)


class MissingTenantContext(RuntimeError):
    """Raised when code attempts a tenant-scoped operation without tenant context."""


def get_tenant_id() -> str:
    """Retrieve the active tenant ID, failing closed unless legacy mode is explicit."""
    tenant_id = tenant_id_var.get()
    if tenant_id:
        return tenant_id
    if os.getenv("CORTEX_LEGACY_DEFAULT_TENANT") == "1":
        return "default"
    raise MissingTenantContext("Tenant context missing")
