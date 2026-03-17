import pytest

from cortex.guards.capabilities import Capability, RiskTier
from cortex.guards.capability_guard import CapabilityGuard


@pytest.fixture
def analytics_guard() -> CapabilityGuard:
    """A guard restricted strictly to analytical read."""
    caps = {
        Capability(name="fs:read", tier=RiskTier.TIER_1_LOCAL_SAFE),
        Capability(name="mem:query", tier=RiskTier.TIER_0_ANALYTICAL),
    }
    return CapabilityGuard(allowed_capabilities=caps)


@pytest.fixture
def execution_guard() -> CapabilityGuard:
    """A guard capable of local mutations."""
    caps = {
        Capability(name="fs:read", tier=RiskTier.TIER_1_LOCAL_SAFE),
        Capability(name="fs:write", tier=RiskTier.TIER_3_LOCAL_MUTATION),
        Capability(name="git:commit", tier=RiskTier.TIER_3_LOCAL_MUTATION),
    }
    return CapabilityGuard(allowed_capabilities=caps)


def test_capability_guard_success(analytics_guard: CapabilityGuard) -> None:
    # Action matches capability exactly and requested tier is below max tier
    analytics_guard.validate_action("fs:read", RiskTier.TIER_1_LOCAL_SAFE)
    analytics_guard.validate_action("mem:query", RiskTier.TIER_0_ANALYTICAL)


def tier_escalation_violation(analytics_guard: CapabilityGuard) -> None:
    # Attempting to escalate the requested tier above the allowed maximum
    with pytest.raises(ValueError, match="exceeds max allowed Tier"):
        # Although "fs:read" is present, the action requests TIER_3 which is blocked
        analytics_guard.validate_action("fs:read", RiskTier.TIER_3_LOCAL_MUTATION)


def missing_capability_violation(execution_guard: CapabilityGuard) -> None:
    # The guard allows tier 3, but specifically lacks the "network:get" capability
    with pytest.raises(ValueError, match="Missing required capability 'network:get'"):
        execution_guard.validate_action("network:get", RiskTier.TIER_2_REMOTE_READ)


def test_dynamic_capability_grant(analytics_guard: CapabilityGuard) -> None:
    # Initially max tier is 1
    assert analytics_guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE

    # Add a Tier 3 capability dynamically
    analytics_guard.add_capability(Capability(name="fs:write", tier=RiskTier.TIER_3_LOCAL_MUTATION))

    # Max tier elevates
    assert analytics_guard.max_allowed_tier == RiskTier.TIER_3_LOCAL_MUTATION

    # We can now write
    analytics_guard.validate_action("fs:write", RiskTier.TIER_3_LOCAL_MUTATION)


def test_capability_revocation(execution_guard: CapabilityGuard) -> None:
    # Initially max tier is 3
    assert execution_guard.max_allowed_tier == RiskTier.TIER_3_LOCAL_MUTATION

    execution_guard.revoke_capability("fs:write")
    execution_guard.revoke_capability("git:commit")

    # Tier downgrades accurately to the remaining capabilities
    assert execution_guard.max_allowed_tier == RiskTier.TIER_1_LOCAL_SAFE

    with pytest.raises(ValueError, match="Execution rejected: Requested Tier"):
        execution_guard.validate_action("fs:write", RiskTier.TIER_3_LOCAL_MUTATION)
