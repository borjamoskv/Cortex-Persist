import logging

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier

logger = logging.getLogger("cortex.guards.capability_guard")


class CapabilityGuard:
    """
    Enforces capability and risk tier constraints on execution.
    Acts as the deterministic membrane preventing generative outputs
    from executing un-granted operations.
    """

    def __init__(self, credentials: AgentCredentials):
        """Builds a deterministic guard bound to an agent's operational profile."""
        self.credentials = credentials
        # A mutable set is kept for scoped degradation (revocation)
        self.active_capabilities = set(credentials.capabilities)
        # We cap the active tier by the credentials' hard ceiling
        self._recalculate_effective_tier()

    def _recalculate_effective_tier(self) -> None:
        """Calculates the max permissible tier bounded by hard agent limits."""
        if not self.active_capabilities:
            self.max_allowed_tier = RiskTier.TIER_0_ANALYTICAL
            return

        highest_active = max(cap.tier for cap in self.active_capabilities)
        self.max_allowed_tier = min(highest_active, self.credentials.max_tier)

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

        logger.debug(
            "Action validated: %s at Tier %s", required_capability_name, requested_tier.name
        )

    def add_capability(self, capability: Capability) -> None:
        """Dynamically grant a capability, escalating tier if needed."""
        self.active_capabilities.add(capability)
        # Escalate hard ceiling if the new cap demands it
        if capability.tier > self.credentials.max_tier:
            object.__setattr__(self.credentials, "max_tier", capability.tier)
        self._recalculate_effective_tier()

    def revoke_capability(self, capability_name: str) -> None:
        """Revoke a capability by name, scoping down execution rights proactively."""
        self.active_capabilities = {
            cap for cap in self.active_capabilities if cap.name != capability_name
        }
        self._recalculate_effective_tier()

    def __repr__(self) -> str:
        caps = [cap.name for cap in self.active_capabilities]
        return f"<CapabilityGuard agent={self.credentials.agent_id} max_tier={self.max_allowed_tier.name} caps={caps}>"
