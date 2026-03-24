import logging

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier

logger = logging.getLogger("cortex.guards.capability_guard")


class CapabilityGuard:
    """
    Enforces capability and risk tier constraints on execution.
    Acts as the deterministic membrane preventing generative outputs
    from executing un-granted operations.
    """

    def __init__(
        self,
        credentials: AgentCredentials | None = None,
        allowed_capabilities: set[Capability] | None = None,
        max_allowed_tier: RiskTier | None = None,
    ):
        """Builds a deterministic guard bound to an agent's operational profile."""
        if credentials:
            self.credentials = credentials
            self.capabilities = list(credentials.capabilities)
            self.max_allowed_tier = max_allowed_tier or credentials.max_tier
        elif allowed_capabilities is not None:
            # Create dummy credentials for backward compatibility
            self.capabilities = list(allowed_capabilities)
            self.max_allowed_tier = max_allowed_tier or max((cap.tier for cap in allowed_capabilities), default=RiskTier.LOW)
            self.credentials = AgentCredentials(
                agent_id="legacy_agent",
                capabilities=set(self.capabilities),
                max_tier=self.max_allowed_tier
            )
        else:
            self.capabilities = []
            self.max_allowed_tier = max_allowed_tier or RiskTier.LOW
            self.credentials = None

    def add_capability(self, capability: Capability) -> None:
        """Add a capability dynamically, elevating execution rights."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            logger.info("CapabilityGuard — added capability %s", capability.name)

    def can_execute(self, capability_name: str) -> bool:
        """Checks if a capability is present and not exceeding the risk tier."""
        for cap in self.capabilities:
            if cap.name == capability_name:
                if cap.tier.value <= self.max_allowed_tier.value:
                    return True
                else:
                    logger.warning(
                        "CapabilityGuard — %s blocked (Tier %s > Max %s)",
                        capability_name, cap.tier.name, self.max_allowed_tier.name
                    )
                    return False
        return False

    def validate_operation(self, operation: str, tier: RiskTier) -> bool:
        """Validates if an operation of a certain tier is allowed."""
        if tier.value <= self.max_allowed_tier.value:
            return True
        logger.warning(
            "CapabilityGuard — Operation %s blocked (Tier %s > Max %s)",
            operation, tier.name, self.max_allowed_tier.name
        )
        return False
