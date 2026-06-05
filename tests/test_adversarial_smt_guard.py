import pytest
from cortex.guards.smt_guard import SMTConstraintGuard

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
        {"confidence": 0.5, "timestamp": 200}
    ]
    assert guard.validate_consistency(consistent_facts) is True
    
    # 5. Reverse order should fail
    inconsistent_facts = [
        {"confidence": 0.5, "timestamp": 200},
        {"confidence": 0.5, "timestamp": 100}
    ]
    assert guard.validate_consistency(inconsistent_facts) is False

