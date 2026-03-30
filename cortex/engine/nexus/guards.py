"""
CORTEX Nexus: Billing Guard & Admittance Layer
RFC-047 / Project LEVIATHAN
"""

import logging
from typing import Any
from .schema import TenantRegistry

logger = logging.getLogger("cortex.nexus")


class BillingGuard:
    """
    Sovereign Billing Guard.
    Intercepts write proposals and verifies if the tenant has exergy (capital)
    available to sustain the audit trail.
    """

    def __init__(self, registry_provider: Any) -> None:
        self.registry = registry_provider

    async def validate_admittance(self, tenant_id: str) -> bool:
        """
        Enforces the Toll-Gate Lock.
        If balance <= 0, the audit trail is severed, effectively disabling the agent's
        compliance status.
        """
        tenant: Optional[TenantRegistry] = await self.registry.get_tenant(tenant_id)

        if not tenant:
            logger.warning(f"Admittance Denied: Tenant {tenant_id} not found.")
            return False

        if not tenant.is_active:
            logger.warning(f"Admittance Denied: Tenant {tenant_id} is inactive.")
            return False

        if tenant.balance_usd <= 0:
            logger.critical(f"Toll-Gate Lock: Tenant {tenant_id} has zero balance. Audit severed.")
            return False

        return True


class NexusMasterGuard:
    """Orchestrates combined guards for the Nexus Cloud layer."""
    def __init__(self, billing: BillingGuard) -> None:
        self.billing = billing

    async def authorize_write(self, tenant_id: str, proposal: dict[str, Any]) -> bool:
        # 1. Check Billing
        if not await self.billing.validate_admittance(tenant_id):
            return False

        # 2. Check Logical Integrity (future implementation)
        # return await self.integrity_guard.check(proposal)

        return True
