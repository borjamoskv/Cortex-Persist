# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import patch, MagicMock
from babylon60.verification.verifier import SovereignVerifier, VerificationResult
from babylon60.verification.invariants import SafetyInvariant, InvariantSeverity


def test_verifier_initialization_no_z3():
    # Force ImportError on z3
    with patch("builtins.__import__", side_effect=ImportError):
        verifier = SovereignVerifier()
    assert verifier._solver is None
    assert len(verifier.invariants) == 7


def test_verifier_initialization_with_z3():
    # Mock z3 module
    z3_mock = MagicMock()
    solver_mock = MagicMock()
    z3_mock.Solver.return_value = solver_mock

    with patch.dict("sys.modules", {"z3": z3_mock}):
        verifier = SovereignVerifier()
        assert verifier._solver is not None
        solver_mock.set.assert_called_with("timeout", 5000)


def test_verifier_check_safe():
    verifier = SovereignVerifier()
    code = "x = 1"
    result = verifier.check(code, {"file_path": "test.py"})
    assert result.is_valid is True
    assert result.proof_certificate == "Z3_UNSAT_BY_AST_PROXIMAL"
    assert len(result.violations) == 0


def test_verifier_check_unsafe():
    verifier = SovereignVerifier()
    code = "eval('1 + 1')"
    result = verifier.check(code, {"file_path": "test.py"})
    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0]["id"] == "I7"
    assert "Termination Guarantee" in result.violations[0]["name"]
    assert result.counterexample is not None
    assert result.counterexample["file"] == "test.py"


def test_verifier_solver_reset():
    z3_mock = MagicMock()
    solver_mock = MagicMock()
    z3_mock.Solver.return_value = solver_mock

    with patch.dict("sys.modules", {"z3": z3_mock}):
        verifier = SovereignVerifier()
        verifier.check("x = 1")
        solver_mock.reset.assert_called_once()


def test_verifier_custom_invariants():
    custom_inv = [SafetyInvariant(id="C1", name="Custom", description="desc")]
    verifier = SovereignVerifier(invariants=custom_inv)
    assert len(verifier.invariants) == 1
    assert verifier.invariants[0].id == "C1"

    # Trigger a violation that won't match the custom invariant list,
    # falling back to the invariant id as name
    code = "eval('1')"
    result = verifier.check(code)
    assert result.is_valid is False
    assert result.violations[0]["id"] == "I7"
    assert result.violations[0]["name"] == "I7"  # No match found, returns ID
