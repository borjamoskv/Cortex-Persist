from __future__ import annotations

from typing import Optional

"""
CORTEX v6.0 — Antipattern Scanner.

AST-based detection of code quality violations that the GEMINI.md rules
mandate but were never enforced automatically. Each scanner implements
the Meta-Rule: "What information is IMPLICIT in my code that should be EXPLICIT?"

Scanners:
  1. BroadExceptionScanner   → `except Exception` / bare `except:`
  2. AsyncIntegrityScanner   → blocking I/O in async contexts
  3. MagicLiteralScanner     → unnamed numeric/string constants
  4. ImportGraphScanner      → circular deps + fan-out analysis
  5. ImplicitAssumptionScanner → missing type guards, Optional misuse
  6. DeadCodeScanner         → unreachable code after return/raise
"""

import ast
import logging
import os
from pathlib import Path

from cortex.extensions.mejoralo._scanner_import_graph import (
    run_graph_scanners as _run_graph_scanners,
)
from cortex.extensions.mejoralo._scanner_visitors import (
    _AsyncIntegrityVisitor,
    _BroadExceptionVisitor,
)
from cortex.extensions.mejoralo.constants import MAX_FUNC_PARAMS, SKIP_DIRS, TOTAL_SCANNER_COUNT
from cortex.extensions.mejoralo.models import AntipatternFinding, AntipatternReport

__all__ = ["scan_antipatterns"]


# Blocking calls that MUST NOT appear in async functions
_BLOCKING_CALLS: dict[str, str] = {
    "open": "Use aiofiles.open() or asyncio.to_thread(open, ...)",
    "time.sleep": "Use asyncio.sleep()",
    "requests.get": "Use httpx.AsyncClient.get()",
    "requests.post": "Use httpx.AsyncClient.post()",
    "requests.put": "Use httpx.AsyncClient.put()",
    "requests.delete": "Use httpx.AsyncClient.delete()",
    "requests.patch": "Use httpx.AsyncClient.patch()",
    "requests.head": "Use httpx.AsyncClient.head()",
    "requests.request": "Use httpx.AsyncClient.request()",
    "subprocess.run": "Use asyncio.create_subprocess_exec()",
    "subprocess.call": "Use asyncio.create_subprocess_exec()",
    "subprocess.check_output": "Use asyncio.create_subprocess_exec()",
    "os.system": "Use asyncio.create_subprocess_shell()",
    "input": "Use aioconsole.ainput()",
    "urllib.request.urlopen": "Use httpx.AsyncClient",
}

# Magic number whitelist — common constants that are acceptable
_MAGIC_WHITELIST = {0, 1, 2, -1, 100, 0.5}


logger = logging.getLogger("cortex.extensions.mejoralo.antipatterns")


# ── Scanner 3: Magic Literals ────────────────────────────────────────


class _MagicLiteralVisitor(ast.NodeVisitor):
    """Detect unnamed numeric constants and magic strings."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings
        self._in_assignment = False
        self._in_default = False

    def visit_Assign(self, node: ast.Assign) -> None:
        # Module-level CONSTANT = 42 is fine
        if self._is_constant_assignment(node):
            return
        self._in_assignment = True
        self.generic_visit(node)
        self._in_assignment = False

    def visit_arguments(self, node: ast.arguments) -> None:
        # Default values are acceptable
        old = self._in_default
        self._in_default = True
        for default in node.defaults + node.kw_defaults:
            if default:
                self.visit(default)
        self._in_default = old

    def visit_Constant(self, node: ast.Constant) -> None:
        if self._in_default:
            return

        value = node.value
        # Skip strings, None, booleans, Ellipsis
        if isinstance(value, (str, bytes, bool, type(None), type(...))):
            return

        # Skip whitelisted values
        if isinstance(value, (int, float)) and value in _MAGIC_WHITELIST:
            return

        # Check context — is this in a comparison, return, or arithmetic?
        self.findings.append(
            AntipatternFinding(
                scanner="MagicLiteral",
                severity="low",
                file=self.rel,
                line=node.lineno,
                message=f"Magic number `{value}` — unnamed constant obscures intent",
                fix_hint=f"Extract to a named constant: MY_CONSTANT = {value}",
            )
        )

    @staticmethod
    def _is_constant_assignment(node: ast.Assign) -> bool:
        """Check if this is a UPPER_CASE = value pattern."""
        if len(node.targets) != 1:
            return False
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.isupper():
            return True
        return False


# ── Scanner 4: Import Graph → See cortex/mejoralo/_scanner_import_graph.py ──


# ── Scanner 5: Implicit Assumptions ──────────────────────────────────


class _ImplicitAssumptionVisitor(ast.NodeVisitor):
    """Detect patterns where assumptions are implicit instead of explicit."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect dict/list access without guard: d["key"], l[0]."""
        # Only flag direct string/int subscript on bare names
        if (
            isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, (str, int))
        ):
            # Check if this is inside a try block (then it's guarded)
            # We can't easily check ancestry in a simple visitor,
            # so we flag all and let the user triage
            pass  # Intentionally not flagging — too noisy without context
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_return_type_hint(node)
        self._check_too_many_params(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_return_type_hint(node)
        self._check_too_many_params(node)
        self.generic_visit(node)

    def _check_return_type_hint(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Public functions without return type hints hide intent."""
        if node.name.startswith("_"):
            return  # Private functions get a pass
        if node.name in (
            "__init__",
            "__str__",
            "__repr__",
            "__len__",
            "__eq__",
            "__hash__",
            "__bool__",
            "__enter__",
            "__exit__",
            "__aenter__",
            "__aexit__",
        ):
            return  # Dunder methods with obvious returns
        if node.returns is None:
            self.findings.append(
                AntipatternFinding(
                    scanner="ImplicitAssumption",
                    severity="medium",
                    file=self.rel,
                    line=node.lineno,
                    message=f"Public function `{node.name}()` has no return type hint",
                    fix_hint=f"Add return type: def {node.name}(...) -> ReturnType:",
                )
            )

    def _check_too_many_params(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        """Too many parameters is a code smell (implicit complexity)."""
        args = node.args
        total = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
        # Subtract 'self' or 'cls'
        if total > 0 and args.args and args.args[0].arg in ("self", "cls"):
            total -= 1
        if total > MAX_FUNC_PARAMS:
            self.findings.append(
                AntipatternFinding(
                    scanner="ImplicitAssumption",
                    severity="medium",
                    file=self.rel,
                    line=node.lineno,
                    message=(
                        f"Function `{node.name}()` has {total} parameters "
                        f"(max recommended: {MAX_FUNC_PARAMS})"
                    ),
                    fix_hint="Consider grouping parameters into a dataclass or config object.",
                )
            )


# ── Scanner 6: Dead Code ─────────────────────────────────────────────


class _DeadCodeVisitor(ast.NodeVisitor):
    """Detect unreachable code after return/raise/break/continue."""

    def __init__(self, rel: str, findings: list[AntipatternFinding]) -> None:
        self.rel = rel
        self.findings = findings

    def _check_body(self, body: list[ast.stmt]) -> None:
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                # Check if there's code after this statement (in same block)
                remaining = body[i + 1 :]
                # Filter out pass statements and string literals (docstrings)
                real_remaining = [
                    s
                    for s in remaining
                    if not isinstance(s, ast.Pass)
                    and not (
                        isinstance(s, ast.Expr)
                        and isinstance(s.value, ast.Constant)
                        and isinstance(s.value.value, str)
                    )
                ]
                if real_remaining:
                    dead_stmt = real_remaining[0]
                    self.findings.append(
                        AntipatternFinding(
                            scanner="DeadCode",
                            severity="medium",
                            file=self.rel,
                            line=getattr(dead_stmt, "lineno", stmt.lineno + 1),
                            message=f"Unreachable code after `{type(stmt).__name__.lower()}`",
                            fix_hint="Remove dead code or restructure logic.",
                        )
                    )
                break  # Only report first dead block per body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._check_body(node.body)
        self._check_body(node.orelse)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_body(node.body)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._check_body(node.body)
        for handler in node.handlers:
            self._check_body(handler.body)
        self.generic_visit(node)


# ── Orchestrator ─────────────────────────────────────────────────────


def _scan_single_file(
    filepath: Path,
    root: Path,
    findings: list[AntipatternFinding],
) -> None:
    """Run all AST-based scanners on a single Python file."""
    try:
        content = filepath.read_text(errors="replace")
        tree = ast.parse(content)
    except (SyntaxError, OSError):
        return

    rel = str(filepath.relative_to(root))

    # Run all visitors
    _BroadExceptionVisitor(rel, findings).visit(tree)
    _AsyncIntegrityVisitor(rel, findings).visit(tree)
    _MagicLiteralVisitor(rel, findings).visit(tree)
    _ImplicitAssumptionVisitor(rel, findings).visit(tree)
    _DeadCodeVisitor(rel, findings).visit(tree)


def _gather_python_files(root: Path) -> Optional[tuple[list[Path], Path]]:
    """Gather Python files to scan and determine the scan root."""
    if root.is_file():
        return [root], root.parent

    if root.is_dir():
        files = []
        for dirpath, dirs, filenames in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".py"):
                    files.append(Path(dirpath) / f)
        return files, root

    return None


# _run_graph_scanners → imported from _scanner_import_graph at module top


def scan_antipatterns(
    path: str | Path,
    *,
    root_package: str = "cortex",
    include_magic: bool = False,
    include_type_hints: bool = True,
) -> AntipatternReport:
    """Execute full antipattern scan on a Python project.

    Args:
        path: Project root directory or single file.
        root_package: Package name for fan-out analysis.
        include_magic: Enable magic literal detection (noisy, off by default).
        include_type_hints: Enable missing type hint detection.

    Returns:
        AntipatternReport with all findings.
    """
    root = Path(path).resolve()
    report = AntipatternReport()

    result = _gather_python_files(root)
    if result is None:
        logger.error("Path is not a file or directory: %s", root)
        return report

    files, scan_root = result

    report.files_scanned = len(files)
    findings: list[AntipatternFinding] = []

    # ── AST-based scanners (per file) ──
    for fp in files:
        _scan_single_file(fp, scan_root, findings)

    # ── Import graph scanners (project-wide) ──
    if root.is_dir():
        _run_graph_scanners(scan_root, root_package, findings)

    # ── Filter by configuration ──
    if not include_magic:
        findings = [f for f in findings if f.scanner != "MagicLiteral"]
    if not include_type_hints:
        findings = [
            f
            for f in findings
            if not (f.scanner == "ImplicitAssumption" and "return type hint" in f.message)
        ]

    report.findings = sorted(
        findings,
        key=lambda f: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4),
            f.file,
            f.line,
        ),
    )
    report.scanners_run = TOTAL_SCANNER_COUNT

    return report
