# [C5-REAL] Exergy-Maximized
import pytest

from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier
from cortex.guards.capability_guard import CapabilityGuard


@pytest.fixture
def analytics_guard() -> CapabilityGuard:
    """A guard restricted strictly to analytical read."""
    caps = {
        Capability(name="fs:read", tier=RiskTier.TIER_1_LOCAL_SAFE),
        Capability(name="mem:query", tier=RiskTier.TIER_0_ANALYTICAL),
    }
    creds = AgentCredentials(
        agent_id="test-analyst",
        capabilities=caps,
        max_tier=RiskTier.TIER_1_LOCAL_SAFE,
    )
    return CapabilityGuard(credentials=creds)


@pytest.fixture
def execution_guard() -> CapabilityGuard:
    """A guard capable of local mutations."""
    caps = {
        Capability(name="fs:read", tier=RiskTier.TIER_1_LOCAL_SAFE),
        Capability(name="fs:write", tier=RiskTier.TIER_3_LOCAL_MUTATION),
        Capability(name="git:commit", tier=RiskTier.TIER_3_LOCAL_MUTATION),
    }
    creds = AgentCredentials(
        agent_id="test-executor",
        capabilities=caps,
        max_tier=RiskTier.TIER_3_LOCAL_MUTATION,
    )
    return CapabilityGuard(credentials=creds)


def test_capability_guard_success(analytics_guard: CapabilityGuard) -> None:
    # Action matches capability exactly and requested tier is below max tier
    analytics_guard.validate_action("fs:read", RiskTier.TIER_1_LOCAL_SAFE)
    analytics_guard.validate_action("mem:query", RiskTier.TIER_0_ANALYTICAL)


def test_tier_escalation_violation(analytics_guard: CapabilityGuard) -> None:
    # Attempting to escalate the requested tier above the allowed maximum
    with pytest.raises(ValueError, match="exceeds max allowed Tier"):
        # Although "fs:read" is present, the action requests TIER_3 which is blocked
        analytics_guard.validate_action("fs:read", RiskTier.TIER_3_LOCAL_MUTATION)


def test_missing_capability_violation(execution_guard: CapabilityGuard) -> None:
    # The guard allows tier 3, but specifically lacks the "network:get" capability
    with pytest.raises(ValueError, match="Missing required capability 'network:get'"):
        execution_guard.validate_action("network:get", RiskTier.TIER_2_REMOTE_READ)


def test_dynamic_capability_grant_with_high_ceiling() -> None:
    # Setup agent with a high ceiling so tier elevation can be observed
    caps = {Capability(name="fs:read", tier=RiskTier.TIER_1_LOCAL_SAFE)}
    creds = AgentCredentials(
        agent_id="test-elevatable",
        capabilities=caps,
        max_tier=RiskTier.TIER_4_REMOTE_MUTATION,
    )
    guard = CapabilityGuard(credentials=creds)

    # Initially max tier is 1
    assert guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE

    # Add a Tier 3 capability dynamically
    guard.grant_capability(Capability(name="fs:write", tier=RiskTier.TIER_3_LOCAL_MUTATION))

    # Max tier elevates to 3
    assert guard.max_allowed_tier == RiskTier.TIER_3_LOCAL_MUTATION

    # We can now write
    guard.validate_action("fs:write", RiskTier.TIER_3_LOCAL_MUTATION)


def test_grant_beyond_ceiling_is_capped(analytics_guard: CapabilityGuard) -> None:
    # analytics_guard has max_tier = TIER_1_LOCAL_SAFE
    assert analytics_guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE

    # Granting TIER_3 should still result in TIER_1 ceiling enforcement
    analytics_guard.grant_capability(
        Capability(name="fs:write", tier=RiskTier.TIER_3_LOCAL_MUTATION)
    )
    assert analytics_guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE


def test_capability_revocation(execution_guard: CapabilityGuard) -> None:
    # Initially max tier is 3
    assert execution_guard.max_allowed_tier == RiskTier.TIER_3_LOCAL_MUTATION

    execution_guard.revoke_capability("fs:write")
    execution_guard.revoke_capability("git:commit")

    # Tier downgrades accurately to the remaining capabilities
    assert execution_guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE

    with pytest.raises(ValueError, match="Execution rejected: Requested Tier"):
        execution_guard.validate_action("fs:write", RiskTier.TIER_3_LOCAL_MUTATION)
