# [C5-REAL] Exergy-Maximized
"""RustChain Open Judge Gate Interface.

Implements AST-lint, Test-Runner, and Policy Judges with Ed25519 signing.
"""

from __future__ import annotations

import ast
import time
from abc import ABC, abstractmethod
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519


class Judge(ABC):
    """Abstract base class for all Open Judge implementations."""

    @abstractmethod
    async def judge(
        self, code: str, config: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        """Judge the provided code based on internal rules and config.

        Returns:
            Tuple[bool, List[str]]: (passed_or_not, list_of_failure_reasons)
        """
        pass

    @staticmethod
    def sign_verdict(
        private_key_bytes: bytes,
        passed: bool,
        reasons: list[str],
    ) -> dict[str, Any]:
        """Sign a verdict using Ed25519 private key.

        Args:
            private_key_bytes: Raw private key bytes.
            passed: The test result.
            reasons: List of reasons for the decision.
        """
        timestamp = int(time.time())
        reasons_str = ",".join(reasons)
        payload = f"{passed}:{reasons_str}:{timestamp}".encode()

        priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = priv_key.sign(payload)

        return {
            "passed": passed,
            "reasons": reasons,
            "timestamp": timestamp,
            "signature": signature.hex(),
        }

    @staticmethod
    def verify_verdict(verdict_packet: dict[str, Any], public_key_bytes: bytes) -> bool:
        """Verify an Ed25519 signature on a verdict packet."""
        try:
            passed = verdict_packet["passed"]
            reasons = verdict_packet["reasons"]
            timestamp = verdict_packet["timestamp"]
            signature = bytes.fromhex(verdict_packet["signature"])

            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)

            reasons_str = ",".join(reasons)
            payload = f"{passed}:{reasons_str}:{timestamp}".encode()

            pub_key.verify(signature, payload)
            return True
        except (ValueError, TypeError, OSError, KeyError):
            return False
        except Exception as e:
            if "InvalidSignature" in type(e).__name__:
                return False
            raise


class ASTLintJudge(Judge):
    """Static analysis judge checking code syntax and structures using python AST."""

    async def judge(
        self, code: str, config: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        cfg = config or {}
        banned_terms = cfg.get("banned_terms", ["eval", "exec"])
        require_docstrings = cfg.get("require_docstrings", False)

        reasons: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"SyntaxError: {e}"]

        class LintVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.has_bare_except = False
                self.found_banned: list[str] = []
                self.missing_docstrings: list[str] = []

            def visit_Name(self, node: ast.Name) -> None:
                if node.id in banned_terms:
                    self.found_banned.append(node.id)
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name) and node.func.id in banned_terms:
                    self.found_banned.append(node.func.id)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.type is None:
                    self.has_bare_except = True
                self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                if require_docstrings and ast.get_docstring(node) is None:
                    self.missing_docstrings.append(f"Function {node.name}")
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if require_docstrings and ast.get_docstring(node) is None:
                    self.missing_docstrings.append(f"Class {node.name}")
                self.generic_visit(node)

            def visit_Module(self, node: ast.Module) -> None:
                if require_docstrings and ast.get_docstring(node) is None:
                    self.missing_docstrings.append("Module")
                self.generic_visit(node)

        visitor = LintVisitor()
        visitor.visit(tree)

        for term in sorted(set(visitor.found_banned)):
            reasons.append(f"Use of banned term: {term}")
        if visitor.has_bare_except:
            reasons.append("Use of bare except block")
        for item in sorted(visitor.missing_docstrings):
            reasons.append(f"Missing docstring: {item}")

        return len(reasons) == 0, reasons


class TestRunnerJudge(Judge):
    """Spawns a pytest subprocess to execute tests against the submitted code."""

    async def judge(
        self, code: str, config: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        cfg = config or {}
        test_code = cfg.get("test_code")
        timeout = cfg.get("timeout", 5.0)

        if not test_code:
            return False, ["Missing 'test_code' in config for TestRunnerJudge"]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            sut_file = tmp_path / "solution.py"
            sut_file.write_text(code, encoding="utf-8")

            test_file = tmp_path / "test_solution.py"
            test_file.write_text(test_code, encoding="utf-8")

            # Add tmpdir to python path for pytest to find solution.py
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{tmpdir}{os.pathsep}{env.get('PYTHONPATH', '')}"

            try:
                res = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file)],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                if res.returncode == 0:
                    return True, []
                else:
                    output = res.stdout or ""
                    if res.stderr:
                        output += "\n" + res.stderr
                    return False, [
                        f"pytest failed with exit status {res.returncode}",
                        output.strip(),
                    ]
            except subprocess.TimeoutExpired:
                return False, [f"Test runner timed out after {timeout} seconds"]
            except (ValueError, TypeError, OSError, KeyError) as e:
                return False, [f"Test runner execution failed: {e}"]


class PolicyJudge(Judge):
    """Validates submitted code against policy constraints like line limits and imports."""

    async def judge(
        self, code: str, config: dict[str, Any] | None = None
    ) -> tuple[bool, list[str]]:
        cfg = config or {}
        max_lines = cfg.get("max_lines")
        banned_imports = cfg.get("banned_imports", [])
        min_comment_ratio = cfg.get("min_comment_ratio")

        reasons: list[str] = []
        lines = code.splitlines()
        total_lines = len(lines)

        # 1. Max lines
        if max_lines is not None and total_lines > max_lines:
            reasons.append(f"Line count ({total_lines}) exceeds maximum permitted ({max_lines})")

        # 2. Banned imports using AST
        try:
            tree = ast.parse(code)

            class ImportVisitor(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.imports: list[str] = []

                def visit_Import(self, node: ast.Import) -> None:
                    for alias in node.names:
                        self.imports.append(alias.name)
                    self.generic_visit(node)

                def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                    if node.module:
                        self.imports.append(node.module)
                    self.generic_visit(node)

            visitor = ImportVisitor()
            visitor.visit(tree)

            for imp in visitor.imports:
                for banned in banned_imports:
                    if imp == banned or imp.startswith(banned + "."):
                        reasons.append(f"Import of banned library: {imp}")
        except (ValueError, TypeError, OSError, KeyError):
            # Fallback to text check if AST fails
            for banned in banned_imports:
                for line in lines:
                    if banned in line and ("import" in line or "from" in line):
                        reasons.append(f"Detected potential banned import line: {line.strip()}")

        # 3. Comment ratio
        if min_comment_ratio is not None and total_lines > 0:
            comment_lines = 0.0
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    comment_lines += 1.0
                elif "#" in line:
                    comment_lines += 0.5
            ratio = comment_lines / total_lines
            if ratio < min_comment_ratio:
                reasons.append(
                    f"Comment ratio ({ratio:.2f}) is below the required minimum ({min_comment_ratio:.2f})"
                )

        return len(reasons) == 0, reasons
