"""Sovereign Arbiter — The Strict Validation Membrane (Ω₃).

Implements the Byzantine Default: I verify, then trust.
Any code mutation from the LLM Engine must pass structural checks before
touching the physical disk.
"""

import ast
import logging
from pathlib import Path

logger = logging.getLogger("cortex.engine.sovereign_arbiter")


class ImportPolicyVisitor(ast.NodeVisitor):
    """AST Visitor to enforce CORTEX Phase 3 Import Policy.

    Axiom Ω₃: Byzantine Default. Reject all code that attempts to bypass
    the SovereignSys exoskeleton via raw os/subprocess.
    """

    BLOCKED_MODULES = frozenset({"os", "subprocess", "shutil", "telnetlib", "smtplib", "urllib"})

    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name.split(".")[0] in self.BLOCKED_MODULES:
                self.violations.append(
                    f"Forbidden Import: '{alias.name}' (Use SovereignSys instead)."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and node.module.split(".")[0] in self.BLOCKED_MODULES:
            self.violations.append(
                f"Forbidden Import: 'from {node.module} import ...' (Use SovereignSys)."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Catch dynamic imports or direct system calls if possible via name
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__"):
                self.violations.append(f"Forbidden Dynamic Exec: '{node.func.id}()'.")
        self.generic_visit(node)


class SovereignArbiter:
    """Invoked by Aether Tool Action: write_file.

    Acts as an immune system, preventing the persistence of syntactically
    broken or malicious code (EXOSKELETON Policy) onto the local filesystem.
    """

    # Files allowed to use core OS utilities (The "Trusted Base").
    _TRUSTED_BASE = frozenset(
        {"cortex/utils/syscall.py", "cortex/crypto/vault.py", "cortex/guards/"}
    )

    @classmethod
    def validate_mutation(cls, code_string: str, file_path: str | Path) -> tuple[bool, str]:
        """Validate if the incoming code is safe to write to the given path."""
        path = str(file_path)

        if path.endswith(".py"):
            return cls._validate_python(code_string, path)

        return True, ""

    @classmethod
    def _validate_python(cls, code_string: str, file_path: str) -> tuple[bool, str]:
        """Strictly validate Python syntax and policy. Zero-mercy."""
        try:
            # 1. AST Structural parsing
            tree = ast.parse(code_string, filename=file_path)

            # 2. Strict C-level byte compilation check
            compile(code_string, file_path, "exec")

            # 3. EXOSKELETON Policy Check (Ω₃)
            if not any(trusted in file_path for trusted in cls._TRUSTED_BASE):
                visitor = ImportPolicyVisitor()
                visitor.visit(tree)
                if visitor.violations:
                    msg = (
                        f"[BLOQUEO BIZANTINO - Ω₃] Policy Violation on mutation:\n"
                        f"File: {file_path}\n"
                        f"Violations: {'; '.join(visitor.violations)}\n"
                        f"Aborting write. You MUST use the SovereignSys interface for I/O and shell operations."
                    )
                    logger.warning("🛡️ Policy Block: %s", msg)
                    return False, msg

            return True, ""

        except SyntaxError as e:
            msg = (
                f"[BLOQUEO BIZANTINO - Ω₃] SyntaxError on mutated code:\n"
                f"File: {file_path}, Line {e.lineno}, Offset {e.offset}\n"
                f"Reason: {e.msg}\n"
                f"Aborting write. You MUST correct this syntax error and try again."
            )
            logger.warning("🛡️ Sovereign Arbiter Block: %s", msg)
            return False, msg

        except Exception as e:  # noqa: BLE001 — execution arbiter must catch all fatal compilation errors
            msg = f"[BLOQUEO BIZANTINO - Ω₃] Compilation Failed: {e}"
            logger.error("🛡️ Sovereign Arbiter Compilation Block: %s", msg)
            return False, msg
