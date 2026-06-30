# [C5-REAL] Exergy-Maximized
import pytest
from babylon60.guards.smt_guard import SMTConstraintGuard


def test_adversarial_kill_mutants_smt_guard():
    """
    Adversarial test autonomously generated to kill mutations in smt_guard.py
    Specifically targeting missing return value assertions and boundary inversions.
    """
    guard = SMTConstraintGuard()

    # 1. Test validate_fact returns boolean True/False (not None)
    # This kills the `return None` bug at line 52
    valid_fact = {"confidence": 0.5, "timestamp": 123456789.0}
    assert guard.validate_fact(valid_fact) is True, "validate_fact must explicitly return True"

    # 2. Test bounds checking inversions (confidence > 1.0)
    invalid_conf = {"confidence": 1.5, "timestamp": 123456789.0}
    assert guard.validate_fact(invalid_conf) is False, "confidence > 1.0 must be rejected"

    # 3. Test timestamp <= 0 inversion
    invalid_ts = {"confidence": 0.5, "timestamp": -10.0}
    assert guard.validate_fact(invalid_ts) is False, "timestamp <= 0 must be rejected"


def test_adversarial_consistency():
    guard = SMTConstraintGuard()

    # 4. Test consistency logic (temporal ordering)
    consistent_facts = [
        {"confidence": 0.5, "timestamp": 100},
        {"confidence": 0.5, "timestamp": 200},
    ]
    assert guard.validate_consistency(consistent_facts) is True

    # 5. Reverse order should fail
    inconsistent_facts = [
        {"confidence": 0.5, "timestamp": 200},
        {"confidence": 0.5, "timestamp": 100},
    ]
    assert guard.validate_consistency(inconsistent_facts) is False


def test_unsat_core_isolation():
    guard = SMTConstraintGuard()

    # Temporal ordering violation
    inconsistent_facts = [
        {"confidence": 0.5, "timestamp": 200},
        {"confidence": 0.5, "timestamp": 100},
    ]
    core = guard.isolate_unsat_core(inconsistent_facts)
    assert any("Temporal ordering violation" in c for c in core)

    # Subject consistency violation
    inconsistent_subj = [
        {"subject": "test_subj", "confidence": 0.1, "timestamp": 100},
        {"subject": "test_subj", "confidence": 0.9, "timestamp": 101},
    ]
    core_subj = guard.isolate_unsat_core(inconsistent_subj)
    assert any("Confidence consistency violation on subject" in c for c in core_subj)

    # Audit report format includes unsat_core
    report = guard.audit_report(inconsistent_subj)
    assert report["consistent"] is False
    assert len(report["unsat_core"]) > 0
