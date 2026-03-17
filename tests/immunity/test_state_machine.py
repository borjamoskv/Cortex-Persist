import pytest

from cortex.immunity.policy import (
    assert_not_mutated,
    can_transition,
    classify_risk,
    detect_necrosis,
    next_state_from_profile,
    run_guard_checks,
    seal_artifact,
    transition_artifact,
)
from cortex.immunity.types import (
    ImmuneArtifact,
    ImmunityState,
    PathogenProfile,
    RiskLevel,
    SealViolation,
)


def test_valid_transitions():
    assert can_transition(ImmunityState.OBSERVED, ImmunityState.QUARANTINED)
    assert can_transition(ImmunityState.OBSERVED, ImmunityState.PROMOTABLE)
    assert can_transition(ImmunityState.QUARANTINED, ImmunityState.NECROTIC)
    assert can_transition(ImmunityState.PROMOTABLE, ImmunityState.SEALED)
    assert can_transition(ImmunityState.SEALED, ImmunityState.NECROTIC)
    assert can_transition(ImmunityState.NECROTIC, ImmunityState.AMPUTATED)

    # Invalid transitions
    assert not can_transition(ImmunityState.OBSERVED, ImmunityState.SEALED)
    assert not can_transition(ImmunityState.SEALED, ImmunityState.PROMOTABLE)
    assert not can_transition(ImmunityState.AMPUTATED, ImmunityState.PROMOTABLE)


def test_transition_artifact():
    artifact = ImmuneArtifact(artifact_id="art-1", artifact_type="memory", payload={})
    assert artifact.state == ImmunityState.OBSERVED

    transition_artifact(artifact, ImmunityState.QUARANTINED, "High risk detected")
    assert artifact.state == ImmunityState.QUARANTINED
    assert "High risk detected" in artifact.reasons

    with pytest.raises(ValueError, match="Invalid immunity transition"):
        transition_artifact(artifact, ImmunityState.SEALED)


def test_classify_risk():
    assert classify_risk(0.9) == RiskLevel.CRITICAL
    assert classify_risk(0.7) == RiskLevel.HIGH
    assert classify_risk(0.5) == RiskLevel.MEDIUM
    assert classify_risk(0.2) == RiskLevel.LOW


def test_next_state_from_profile():
    # Low risk
    low_risk = PathogenProfile(0.1, 0.1, 0.9, 0.1, 0.1, 0.1, 0.9, 0.1)
    assert next_state_from_profile(low_risk) == ImmunityState.PROMOTABLE

    # Critical risk
    critical_risk = PathogenProfile(0.9, 0.9, 0.1, 0.9, 0.9, 0.9, 0.1, 0.9)
    assert next_state_from_profile(critical_risk) == ImmunityState.NECROTIC


def test_guard_checks():
    payload_ok = {"schema_version": "1.0", "source": "agent"}
    assert run_guard_checks(payload_ok) == []

    payload_bad = {}
    violations = run_guard_checks(payload_bad)
    assert "missing_schema_version" in violations
    assert "missing_provenance_source" in violations


def test_detect_necrosis():
    assert detect_necrosis(0.8, 0.9, 0.1, 1) is True  # High contradiction
    assert detect_necrosis(0.1, 0.2, 0.1, 1) is True  # Low provenance
    assert detect_necrosis(0.1, 0.9, 0.3, 1) is True  # High infected ancestors
    assert detect_necrosis(0.1, 0.9, 0.1, 5) is True  # High rewrite count
    assert detect_necrosis(0.1, 0.9, 0.1, 1) is False  # Healthy


def test_sealing():
    artifact = ImmuneArtifact(
        artifact_id="art-2",
        artifact_type="doc",
        payload={"data": "test"},
        state=ImmunityState.PROMOTABLE,
    )

    seal = seal_artifact(artifact)
    assert artifact.state == ImmunityState.SEALED
    assert artifact.sealed_at is not None
    assert seal.artifact_id == "art-2"

    # Verify exact same payload
    assert_not_mutated(seal, {"data": "test"})

    # Detect mutation
    with pytest.raises(SealViolation, match="has been mutated"):
        assert_not_mutated(seal, {"data": "test2"})

    # Cannot seal if not promotable
    artifact_bad = ImmuneArtifact(
        artifact_id="art-3",
        artifact_type="doc",
        payload={"data": "test"},
        state=ImmunityState.OBSERVED,
    )
    with pytest.raises(SealViolation, match="must be promotable"):
        seal_artifact(artifact_bad)
