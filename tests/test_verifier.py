"""Tests for CORTEX v7 Sovereign Verifier (Phase 2)."""

import pytest
from cortex.verification.verifier import SovereignVerifier


def test_verifier_safe_code():
    """Test that valid code passes the verification gate."""
    verifier = SovereignVerifier()
    code = """
def process_data(x):
    return x * 2
    """
    result = verifier.check(code, {"file_path": "safe.py"})
    assert result.is_valid
    assert result.proof_certificate == "Z3_UNSAT_BY_AST_PROXIMAL"


def test_verifier_ledger_append_only_violation():
    """Test that attempting to delete from the ledger triggers I2 violation."""
    verifier = SovereignVerifier()
    
    # Code that triggers the 'delete' + 'ledger' pattern (simulated in Phase 2)
    # Actually, my Extractor triggers I2 on ANY 'delete' call for now.
    code = """
async def malicious_delete(ledger):
    await ledger.delete("event_001")
    """
    result = verifier.check(code, {"file_path": "malicious.py"})
    
    assert not result.is_valid
    assert any(v["id"] == "I2" for v in result.violations)
    assert result.counterexample["file"] == "malicious.py"


def test_verifier_eval_violation():
    """Test that use of 'eval' triggers I7 violation."""
    verifier = SovereignVerifier()
    code = "eval('1+1')"
    result = verifier.check(code)
    
    assert not result.is_valid
    assert any(v["id"] == "I7" for v in result.violations)
