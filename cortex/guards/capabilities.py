from dataclasses import dataclass, field
from enum import Enum


class RiskTier(int, Enum):
    """
    Hierarchical risk tiers for action execution.
    Higher tiers require exponentially higher justification and confidence.
    """

    TIER_0_ANALYTICAL = 0  # Local processing, zero side effects
    TIER_1_LOCAL_SAFE = 1  # Sandboxed tools, pure functions
    TIER_2_REMOTE_READ = 2  # API queries, data fetching
    TIER_3_LOCAL_MUTATION = 3  # File modification, local settings
    TIER_4_REMOTE_MUTATION = 4  # Money, permissions, production infra


@dataclass(frozen=True)
class Capability:
    """
    Explicit executable permission granted to an agent or subsystem.
    """

    name: str = field(
        metadata={"description": "Unique capability identifier e.g., 'fs:read', 'network:get'"}
    )
    tier: RiskTier = field(
        metadata={"description": "Operational risk tier associated with this capability"}
    )
    description: str = field(
        default="", metadata={"description": "Readable description of what the capability permits"}
    )


@dataclass(frozen=True)
class AgentCredentials:
    """
    Cryptographic-ready operational profile binding an agent instance to explicit boundaries.
    Enforces maximum thermodynamic entropy (RiskTier) and permitted action scopes.
    """

    agent_id: str = field(
        metadata={"description": "Unique identifier of the agent assuming these credentials."}
    )
    capabilities: set[Capability] = field(
        default_factory=set, metadata={"description": "Explicitly granted capabilities."}
    )
    max_tier: RiskTier = field(
        default=RiskTier.TIER_0_ANALYTICAL,
        metadata={"description": "Absolute ceiling for operations executed by this agent."},
    )
