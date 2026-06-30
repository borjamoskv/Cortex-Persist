import pytest
from babylon60.guards.exergy_guard import ExergyGuard, LandauerGuard


def test_exergy_guard_approves_dense_invariant():
    guard = ExergyGuard()
    # A valid dense invariant without slop
    content = "Axiom 1: Deterministic state mutations must bypass stochastic inference loops. Execution is C5-REAL."
    # Should not raise
    score = guard.check_thermodynamic_yield(content, project="TEST", fact_type="thought")
    assert score >= 0.55


def test_exergy_guard_rejects_conversational_slop():
    guard = ExergyGuard()
    # Slop and very little substance
    content = "Por supuesto, aquí tienes el código. Espero que te sea útil para tu proyecto de base de datos."

    with pytest.raises(ValueError) as exc_info:
        guard.check_thermodynamic_yield(content, project="TEST", fact_type="thought")

    assert "Thermodynamic Violation: Exergy score too low" in str(exc_info.value)


def test_landauer_guard_approves_high_entropy():
    guard = LandauerGuard()
    # High entropy content (e.g. SHA3 hash or math)
    content = "hashlib.sha3_256(b'deterministic_payload').hexdigest() == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"
    # Should not raise for sacred axiom
    entropy = guard.check_landauer_limit(content, is_sacred=True)
    assert entropy >= 4.0


def test_landauer_guard_rejects_low_entropy_sacred_axiom():
    guard = LandauerGuard()
    # A very repetitive string with low entropy
    content = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    with pytest.raises(ValueError) as exc_info:
        guard.check_landauer_limit(content, is_sacred=True)

    assert "Landauer Violation: Thermodynamic density too low" in str(exc_info.value)
