import pytest
import sys
from unittest.mock import patch, MagicMock

from cortex.verification.verifier import SovereignVerifier, VerificationResult
from cortex.verification.invariants import SafetyInvariant


def test_verifier_init_with_z3():
    verifier = SovereignVerifier()
    assert verifier._solver is not None
    # Just to be sure we default to standard invariants
    assert len(verifier.invariants) == 7


def test_verifier_init_without_z3():
    with patch.dict(sys.modules, {"z3": None}):
        verifier = SovereignVerifier()
        assert verifier._solver is None


def test_verifier_check_valid_code():
    verifier = SovereignVerifier()
    code = "x = 1\ny = 2\nprint(x + y)"
    result = verifier.check(code, context={"file_path": "test.py"})

    assert isinstance(result, VerificationResult)
    assert result.is_valid is True
    assert result.violations == []
    assert result.proof_certificate == "Z3_UNSAT_BY_AST_PROXIMAL"


def test_verifier_check_invalid_code():
    verifier = SovereignVerifier()
    # "eval" triggers I7
    code = "eval('1+1')"
    result = verifier.check(code, context={"file_path": "bad.py"})

    assert isinstance(result, VerificationResult)
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0]["id"] == "I7"
    assert "Termination Guarantee" in result.violations[0]["name"]
    assert "Prohibited use of 'eval'" in result.violations[0]["message"]

    assert "findings" in result.counterexample
    assert result.counterexample["file"] == "bad.py"


def test_verifier_check_invalid_code_no_matching_invariant():
    # Provide custom invariants that don't include I7
    custom_invariants = [SafetyInvariant(id="I99", name="Fake Invariant", description="Fake")]
    verifier = SovereignVerifier(invariants=custom_invariants)

    code = "eval('1+1')"  # AST extractor will still emit "I7"
    result = verifier.check(code)

    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0]["id"] == "I7"
    assert (
        result.violations[0]["name"] == "I7"
    )  # Should fallback to id since it's not in our custom_invariants


def test_verifier_check_no_context():
    verifier = SovereignVerifier()
    code = "x = 1"
    result = verifier.check(code)  # no context
    assert result.is_valid is True
