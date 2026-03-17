"""CORTEX v5.2 — Tenancy Context (RLS Support).

Stores and retrieves the tenant ID context dynamically for Row Level Security (RLS)
isolation in the database engine without explicitly passing it down all call chains.
"""

import contextvars

tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="default")


def get_tenant_id() -> str:
    """Retrieve the current active tenant ID from context. Defaults to 'default'."""
    return tenant_id_var.get()
