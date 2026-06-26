# [C5-REAL] Exergy-Maximized
"""
Deterministic AST Grader.

Automated grading bypassing probabilistic LLMs.
Uses Python AST parsing to enforce algorithmic constraints and structural correctness.
Output is binary: Approved or Apoptosis.
"""

import ast
import typing


class ASTGrader(ast.NodeVisitor):
    def __init__(self, required_functions: list[str] = None, forbidden_functions: list[str] = None):
        self.required_functions = set(required_functions or [])
        self.forbidden_functions = set(forbidden_functions or [])
        self.found_functions = set()
        self.violations = []
        self._is_approved = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.found_functions.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_functions:
                self._add_violation(f"Forbidden function call detected: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.forbidden_functions:
                self._add_violation(f"Forbidden attribute call detected: {node.func.attr}")
        self.generic_visit(node)

    def _add_violation(self, message: str) -> None:
        self.violations.append(message)
        self._is_approved = False

    def evaluate(self, code: str) -> bool:
        """Evaluates the code and returns True if Approved, False if Apoptosis."""
        try:
            tree = ast.parse(code)
            self.visit(tree)

            missing = self.required_functions - self.found_functions
            if missing:
                self._add_violation(f"Missing required functions: {missing}")

            return self._is_approved
        except SyntaxError as e:
            self._add_violation(f"Syntax Error: {e}")
            return False


def evaluate_submission(code: str, requirements: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Entry point for deterministic grading."""
    grader = ASTGrader(
        required_functions=requirements.get("required_functions", []),
        forbidden_functions=requirements.get("forbidden_functions", []),
    )

    approved = grader.evaluate(code)

    return {
        "status": "Approved" if approved else "Apoptosis",
        "violations": grader.violations,
        "epistemic_level": "C5-REAL",
    }
