# [C5-REAL] Exergy-Maximized
import pytest
from cortex.guards.z3_anvil import SovereignAnvil, HAS_Z3

class TestSovereignAnvil:
    """
    Formal verification tests for the SovereignAnvil dynamic AST logical parser.
    """
    def test_verify_tautology_sat(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Tautology_Test", "A | ~A")
        assert success is True
        assert proof_hash is not None
        assert "verified" in reason.lower()

    def test_verify_contradiction_unsat(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Contradiction_Test", "A & ~A")
        assert success is False
        assert proof_hash is None
        assert "contradiction" in reason.lower()

    def test_verify_implies_sat(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Implies_Test", "(A & (A => B)) => B")
        assert success is True
        assert proof_hash is not None

    def test_verify_implies_contradiction_unsat(self):
        anvil = SovereignAnvil()
        # A implies B, A is True, but B is False -> contradiction if we assert them all
        success, proof_hash, reason = anvil.verify_rule("Implies_Contradiction", "(A => B) & A & ~B")
        assert success is False
        assert proof_hash is None

    def test_verify_equivalence_sat(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Equivalence_Test", "(A <=> B) & A & B")
        assert success is True

    def test_verify_equivalence_unsat(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Equivalence_Contradiction", "(A <=> B) & A & ~B")
        assert success is False

    def test_verify_syntax_error(self):
        anvil = SovereignAnvil()
        success, proof_hash, reason = anvil.verify_rule("Syntax_Error_Test", "A & & B")
        assert success is False
        assert proof_hash is None
        assert "parsing error" in reason.lower()

    def test_verify_unsupported_ast_node(self):
        anvil = SovereignAnvil()
        # Using a slice or list which is unsupported in boolean logic expressions
        success, proof_hash, reason = anvil.verify_rule("Unsupported_Test", "[A, B]")
        assert success is False
        assert proof_hash is None
        assert "parsing error" in reason.lower()
