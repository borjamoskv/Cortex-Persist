"""CORTEX Hypervisor — Tenant Isolator.

Automatic tenant_id injection and scope enforcement.
The tenant never passes tenant_id manually — it's baked into the AgentHandle
at creation time and threaded through every operation invisibly.
"""

from __future__ import annotations

import logging
import re

__all__ = ["TenantIsolator"]

logger = logging.getLogger("cortex.extensions.hypervisor.isolator")

# Tenant ID: alphanumeric + hyphens + underscores, 1-128 chars
_TENANT_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


class TenantIsolator:
    """Validates and enforces tenant boundaries.

    The Hypervisor creates one Isolator per tenant. All engine calls
    are scoped through this isolator — cross-tenant leakage is
    structurally impossible because the tenant_id is baked in, not
    passed as a parameter.
    """

    __slots__ = ("_tenant_id",)

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = self._validate(tenant_id)

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def scope_kwargs(self, **kwargs: object) -> dict:
        """Inject tenant_id into any engine call kwargs.

        If someone tries to override tenant_id, it's silently corrected.
        The isolator is the source of truth — not the caller.
        """
        kwargs["tenant_id"] = self._tenant_id
        return kwargs

    @staticmethod
    def _validate(tenant_id: str) -> str:
        """Validate tenant_id format. Raises ValueError on bad input."""
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        tid = tenant_id.strip()
        if not _TENANT_PATTERN.match(tid):
            raise ValueError(
                f"Invalid tenant_id: '{tid}'. "
                "Must be 1-128 alphanumeric characters (hyphens/underscores allowed)."
            )
        return tid
