# [C5-REAL] Exergy-Maximized
import pytest
from legacy_research.verification.invariants import InvariantSeverity, SafetyInvariant, SOVEREIGN_INVARIANTS


def test_invariant_severity_enum():
    assert InvariantSeverity.CRITICAL.value == "critical"
    assert InvariantSeverity.WARNING.value == "warning"
    assert InvariantSeverity.INFO.value == "info"


def test_safety_invariant_defaults():
    inv = SafetyInvariant(id="test", name="Test Invariant", description="Test Description")
    assert inv.id == "test"
    assert inv.name == "Test Invariant"
    assert inv.description == "Test Description"
    assert inv.severity == InvariantSeverity.CRITICAL


def test_sovereign_invariants():
    assert len(SOVEREIGN_INVARIANTS) == 7
    ids = [inv.id for inv in SOVEREIGN_INVARIANTS]
    assert "I1" in ids
    assert "I2" in ids
    assert "I3" in ids
    assert "I4" in ids
    assert "I5" in ids
    assert "I6" in ids
    assert "I7" in ids
