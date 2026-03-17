import logging
from typing import Optional

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier

logger = logging.getLogger("cortex.guards.capability_guard")


class CapabilityGuard:
    """
    Enforces capability and risk tier constraints on execution.
    Acts as the deterministic membrane preventing generative outputs
    from executing un-granted operations.

    Two construction modes:
        1. CapabilityGuard(credentials=AgentCredentials(...))
           — legacy path, bound to a full agent profile.
        2. CapabilityGuard(allowed_capabilities={Capability(...)})
           — direct capability set, no agent identity required.
    """

    def __init__(
        self,
        credentials: Optional[AgentCredentials] = None,
        *,
        allowed_capabilities: Optional[set[Capability]] = None,
    ) -> None:
        """Builds a deterministic guard bound to a capability set."""
        if credentials is not None and allowed_capabilities is not None:
            raise ValueError("Provide either 'credentials' or 'allowed_capabilities', not both.")

        if allowed_capabilities is not None:
            # Direct capability set — no agent identity constraints.
            self.credentials = None
            self.active_capabilities: set[Capability] = set(allowed_capabilities)
            self._ceiling = max(
                (cap.tier for cap in self.active_capabilities),
                default=RiskTier.TIER_0_ANALYTICAL,
            )
        elif credentials is not None:
            self.credentials = credentials
            self.active_capabilities = set(credentials.capabilities)
            self._ceiling = credentials.max_tier
        else:
            raise ValueError("Either 'credentials' or 'allowed_capabilities' must be provided.")

        self._recalculate_effective_tier()

    def _recalculate_effective_tier(self) -> None:
        """Calculates the max permissible tier bounded by hard agent limits."""
        highest_active = max(
            (cap.tier for cap in self.active_capabilities), default=RiskTier.TIER_0_ANALYTICAL
        )
        self.max_allowed_tier = min(highest_active, self._ceiling)

    def add_capability(self, capability: Capability) -> None:
        """Dynamically grant a new capability, elevating max_allowed_tier if needed."""
        self.active_capabilities.add(capability)
        # Ceiling stays fixed — only active set changes; tier recomputed.
        # If ceiling was derived from direct caps, raise it with the new cap's tier.
        if self.credentials is None:
            self._ceiling = max(self._ceiling, capability.tier)
        self._recalculate_effective_tier()

    def validate_action(self, required_capability_name: str, requested_tier: RiskTier) -> None:
        """
        Validates if the requested action is permitted based on current capabilities.

        Args:
            required_capability_name: The strict identifier of the capability needed.
            requested_tier: The risk tier of the action being attempted.

        Raises:
            ValueError: If the action is rejected by policy.
        """
        # 1. Tier Validation (Ceiling)
        if requested_tier > self.max_allowed_tier:
            msg = (
                f"Execution rejected: Requested Tier {requested_tier.name} "
                f"exceeds max allowed Tier {self.max_allowed_tier.name}"
            )
            logger.error(msg)
            raise ValueError(msg)

        # 2. Capability Validation (Explicit Allowlist)
        allowed_names = {cap.name for cap in self.active_capabilities}
        if required_capability_name not in allowed_names:
            msg = f"Execution rejected: Missing required capability '{required_capability_name}'"
            logger.error(msg)
            raise ValueError(msg)

        logger.debug("Action validated: %s at Tier %s", required_capability_name, requested_tier.name)

    def revoke_capability(self, capability_name: str) -> None:
        """Revoke a capability by name, scoping down execution rights proactively."""
        self.active_capabilities = {
            cap for cap in self.active_capabilities if cap.name != capability_name
        }
        self._recalculate_effective_tier()

    def __repr__(self) -> str:
        caps = [cap.name for cap in self.active_capabilities]
        agent = self.credentials.agent_id if self.credentials else "<direct>"
        return f"<CapabilityGuard agent={agent} max_tier={self.max_allowed_tier.name} caps={caps}>"
