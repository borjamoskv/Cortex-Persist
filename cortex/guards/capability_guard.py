from __future__ import annotations

import logging
from typing import Optional

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier

logger = logging.getLogger("cortex.guards.capability_guard")


class CapabilityGuard:
    """
    Enforces capability and risk tier constraints on execution.

    Supports two construction modes:
    - Legacy:  CapabilityGuard(credentials=AgentCredentials(...))
    - Direct:  CapabilityGuard(allowed_capabilities={Capability(...)})
    """

    def __init__(
        self,
        credentials: Optional[AgentCredentials] = None,
        *,
        allowed_capabilities: Optional[set[Capability]] = None,
    ) -> None:
        if credentials is not None:
            self.credentials: Optional[AgentCredentials] = credentials
            self.active_capabilities: set[Capability] = set(credentials.capabilities)
            self._hard_ceiling: RiskTier = credentials.max_tier
        elif allowed_capabilities is not None:
            self.credentials = None
            self.active_capabilities = set(allowed_capabilities)
            self._hard_ceiling = RiskTier.TIER_4_REMOTE_MUTATION  # unconstrained ceiling
        else:
            raise TypeError("CapabilityGuard requires either `credentials` or `allowed_capabilities`")

        self._recalculate_effective_tier()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _recalculate_effective_tier(self) -> None:
        """Recalculates the effective max tier from active capabilities."""
        highest_active = max(
            (cap.tier for cap in self.active_capabilities), default=RiskTier.TIER_0_ANALYTICAL
        )
        self.max_allowed_tier = min(highest_active, self._hard_ceiling)

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_action(self, required_capability_name: str, requested_tier: RiskTier) -> None:
        """
        Validates if the requested action is permitted under current capabilities.

        Raises:
            ValueError: If the tier or capability is not satisfied.
        """
        if requested_tier > self.max_allowed_tier:
            msg = (
                f"Execution rejected: Requested Tier {requested_tier.name} "
                f"exceeds max allowed Tier {self.max_allowed_tier.name}"
            )
            logger.error(msg)
            raise ValueError(msg)

        allowed_names = {cap.name for cap in self.active_capabilities}
        if required_capability_name not in allowed_names:
            msg = f"Execution rejected: Missing required capability '{required_capability_name}'"
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(
            "Action validated: %s at Tier %s", required_capability_name, requested_tier.name
        )

    def add_capability(self, cap: Capability) -> None:
        """Dynamically grant a new capability, recalculating the effective tier."""
        self.active_capabilities.add(cap)
        self._recalculate_effective_tier()

    def revoke_capability(self, capability_name: str) -> None:
        """Revoke a capability by name, scoping down execution rights."""
        self.active_capabilities = {
            cap for cap in self.active_capabilities if cap.name != capability_name
        }
        self._recalculate_effective_tier()

    def __repr__(self) -> str:
        caps = [cap.name for cap in self.active_capabilities]
        agent = self.credentials.agent_id if self.credentials else "<direct>"
        return f"<CapabilityGuard agent={agent} max_tier={self.max_allowed_tier.name} caps={caps}>"
