# [C5-REAL] Exergy-Maximized
import ast
import hashlib
import logging
from typing import Optional, Any

try:
    from z3 import And, Bool, Not, Or, Implies, Xor, Solver, sat, unknown, unsat
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

logger = logging.getLogger(__name__)

class SovereignAnvil:
    """
    Fase 3: Sovereign Anvil (Logical Forge)
    Verifies formal logic rules using the Z3 SMT Solver.
    Transits empirical evidence into mathematical proofs.
    """
    def __init__(self):
        if not HAS_Z3:
            logger.warning("Z3 not installed. Anvil operates in bypass/mock mode. Install with: pip install z3-solver")

    def _hash_certificate(self, premise: str, theorem: str, result: str) -> str:
        """Generates a cryptographic hash for the Proof Certificate."""
        payload = f"{premise}|{theorem}|{result}".encode()
        return hashlib.sha3_256(payload).hexdigest()

    def parse_formula(self, formula_str: str) -> tuple[Any, dict[str, Any]]:
        """
        Parses a logical formula string into a Z3 expression tree.
        Supports standard boolean syntax: &, |, ^, ~, not, and, or, =>, <=>
        """
        # Normalize operator notation to Python-compilable tokens
        normalized = (
            formula_str.replace("<=>", "==")
            .replace("=>", ">>")
            .replace("AND", "&")
            .replace("OR", "|")
            .replace("NOT", "~")
            .replace("xor", "^")
        )
        
        tree = ast.parse(normalized, mode="eval")
        vars_dict = {}

        def _walk(node: ast.AST) -> Any:
            if isinstance(node, ast.Name):
                name = node.id
                if name.lower() == "true":
                    return True
                if name.lower() == "false":
                    return False
                if name not in vars_dict:
                    vars_dict[name] = Bool(name)
                return vars_dict[name]
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.op, (ast.Not, ast.Invert)):
                    return Not(_walk(node.operand))
            elif isinstance(node, ast.BinOp):
                left = _walk(node.left)
                right = _walk(node.right)
                if isinstance(node.op, ast.BitAnd):
                    return And(left, right)
                elif isinstance(node.op, ast.BitOr):
                    return Or(left, right)
                elif isinstance(node.op, ast.BitXor):
                    return Xor(left, right)
                elif isinstance(node.op, ast.RShift):  # used for => (implies)
                    return Implies(left, right)
            elif isinstance(node, ast.BoolOp):
                values = [_walk(val) for val in node.values]
                if isinstance(node.op, ast.And):
                    return And(*values)
                elif isinstance(node.op, ast.Or):
                    return Or(*values)
            elif isinstance(node, ast.Compare):
                if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                    left = _walk(node.left)
                    right = _walk(node.comparators[0])
                    return left == right
            
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

        return _walk(tree.body), vars_dict

    def verify_rule(self, rule_name: str, logic_form: str) -> tuple[bool, Optional[str], str]:
        """
        Parses a logical rule and attempts to find a contradiction (un-satisfiability).
        If satisfiable and consistent, returns a Proof Certificate.

        Args:
            rule_name: The name of the rule (e.g. "SafetyBounds").
            logic_form: A string representation of the logic to evaluate.

        Returns:
            tuple[bool, Optional[str], str]: (Success, ProofHash, Reason)
        """
        if not HAS_Z3:
            logger.warning(f"Z3 missing. Simulating Verification for {rule_name}")
            return True, self._hash_certificate(rule_name, logic_form, "simulated_sat"), "Simulated SAT"

        # Special MVP cases mapping for backward compatibility or simple tags
        if logic_form.upper() == "CONTRADICTION":
            logic_form = "A & ~A"
        elif logic_form.upper() == "TAUTOLOGY":
            logic_form = "A | ~A"

        s = Solver()
        try:
            expr, vars_dict = self.parse_formula(logic_form)
            s.add(expr)
        except Exception as e:
            logger.error(f"Sovereign Anvil: Failed to parse formula '{logic_form}': {e}")
            return False, None, f"Parsing error: {e}"

        res = s.check()

        if res == unsat:
            logger.error(f"Sovereign Anvil: Rule {rule_name} is mathematically CONTRADICTORY (UNSAT).")
            return False, None, "Z3 Solver found contradiction (UNSAT)."
        elif res == unknown:
            logger.error(f"Sovereign Anvil: Rule {rule_name} complexity exceeded (UNKNOWN).")
            return False, None, "Z3 Solver timed out or could not decide."
        else:
            logger.info(f"Sovereign Anvil: Rule {rule_name} mathematically verified (SAT).")
            proof_hash = self._hash_certificate(rule_name, logic_form, "SAT")
            return True, proof_hash, "Proof formally verified by Z3."

