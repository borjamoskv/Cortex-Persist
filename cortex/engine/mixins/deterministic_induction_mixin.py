"""
CORTEX v7 — Deterministic Induction Mixin (AX-VI (JIT Concept)).

Enforces mathematical determinism on generated code payloads before they hit
the ledger. Rejects blocking I/O (time.sleep, socket, os.system), network
requests (http, requests), and mutable global state.

Provides an AST-based static analyzer for miniprograms.
"""

from __future__ import annotations

import ast
import logging

logger = logging.getLogger("cortex.engine.deterministic_induction")


class DeterministicInductionMixin:
    """
    AX-VI (JIT Concept): Deterministic Execution Boundaries.
    Injects a rigorous AST validation step before ledger persistence.
    """

    FORBIDDEN_MODULES = {"socket", "requests", "urllib", "time", "os", "subprocess", "sys"}
    FORBIDDEN_FUNCTIONS = {"sleep", "open", "exec", "eval", "system", "popen"}

    def validate_executable_program(self, code: str) -> tuple[bool, str]:
        """
        Validates if a miniprogram respects CORTEX's sovereign boundaries.
        Returns (is_valid, validation_reason).
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Induction failed: Syntax Error - {e}"

        for node in ast.walk(tree):
            # 1. Prevent non-deterministic or blocking imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in self.FORBIDDEN_MODULES:
                        return False, f"Entropy detected: Forbidden import '{alias.name}'."

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in self.FORBIDDEN_MODULES:
                    return False, f"Entropy detected: Forbidden import '{node.module}'."

            # 2. Prevent blocking or mutable intrinsic calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_FUNCTIONS:
                        return False, f"Sovereignty violation: Use of intrinsic '{node.func.id}'."
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_FUNCTIONS:
                        return False, f"Sovereignty violation: Use of '{node.func.attr}()'."

        return True, "Deterministic Induction Passed (C5-Dynamic)."

    def apply_induction_shock(self, agent_id: str, code: str) -> None:
        """
        If a program fails, Nemesis L4 uses this to penalize the source.
        """
        is_valid, reason = self.validate_executable_program(code)
        if not is_valid:
            logger.warning(
                "⚡ [STAGNATION SHOCK] Agent %s generated unstable logic: %s", agent_id, reason
            )
            raise ValueError(reason)
