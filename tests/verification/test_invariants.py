import pytest
from cortex.verification.invariants import SafetyInvariant, SOVEREIGN_INVARIANTS, InvariantSeverity


def test_safety_invariant_creation():
    inv = SafetyInvariant(
        id="T1", name="Test Inv", description="Test Description", severity=InvariantSeverity.WARNING
    )
    assert inv.id == "T1"
    assert inv.name == "Test Inv"
    assert inv.description == "Test Description"
    assert inv.severity == InvariantSeverity.WARNING


def test_sovereign_invariants_length():
    assert len(SOVEREIGN_INVARIANTS) == 7


def test_sovereign_invariants_content():
    ids = [inv.id for inv in SOVEREIGN_INVARIANTS]
    assert "I1" in ids
    assert "I2" in ids
    assert "I3" in ids
    assert "I4" in ids
    assert "I5" in ids
    assert "I6" in ids
    assert "I7" in ids

    # Check defaults
    for inv in SOVEREIGN_INVARIANTS:
        assert inv.severity == InvariantSeverity.CRITICAL
