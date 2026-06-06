"""Mirror Audit: AST-based cyclomatic complexity checker for Cortex-Persist.

Scans Python modules under cortex/ and reports functions that exceed
a configurable complexity threshold. Designed to enforce architectural
simplicity and prevent unbounded cognitive load in agent-facing modules.

Usage (standalone)::

    python -m cortex.audit.mirror_audit
    python -m cortex.audit.mirror_audit --threshold 10 --path cortex/engine
"""
from __future__ import annotations

import ast
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_REPO_ROOT: Path = Path(__file__).parent.parent.parent
_DEFAULT_TARGET: Path = _REPO_ROOT / "cortex"
_DEFAULT_THRESHOLD: int = 10

# Directories excluded from complexity audit
_EXEMPT_DIRS: frozenset[str] = frozenset({
    "__pycache__",
    ".venv",
    "cli",       # CLI layer; complexity is intentional
    "tests",
    "benchmarks",
})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ComplexityViolation:
    """A single function/method that exceeds the complexity threshold."""

    filepath: Path
    function_name: str
    lineno: int
    complexity: int

    def __str__(self) -> str:  # pragma: no cover
        rel = self.filepath.relative_to(_REPO_ROOT)
        return (
            f"{rel}:{self.lineno} '{self.function_name}' "
            f"complexity={self.complexity}"
        )


@dataclass
class AuditReport:
    """Aggregated result of a mirror audit run."""

    threshold: int
    scanned: int = 0
    violations: List[ComplexityViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------

class _ComplexityVisitor(ast.NodeVisitor):
    """Compute McCabe cyclomatic complexity per function via AST traversal."""

    # Branch-introducing node types
    _BRANCH_NODES = (
        ast.If,
        ast.For,
        ast.While,
        ast.ExceptHandler,
        ast.With,
        ast.AsyncFor,
        ast.AsyncWith,
        ast.comprehension,
        ast.Assert,
    )

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold
        self.violations: List[ComplexityViolation] = []
        self._filepath: Path = Path()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def audit_file(self, filepath: Path) -> List[ComplexityViolation]:
        """Parse *filepath* and return violations for this file."""
        self._filepath = filepath
        self.violations = []
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            return []  # skip files with syntax errors gracefully
        self.visit(tree)
        return list(self.violations)

    # ------------------------------------------------------------------
    # Visitor helpers
    # ------------------------------------------------------------------

    def _compute_complexity(self, node: ast.AST) -> int:
        """Return complexity score for *node* (function or async function)."""
        complexity = 1  # base complexity
        for child in ast.walk(node):
            if isinstance(child, self._BRANCH_NODES):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # each additional operand adds a branch
                complexity += len(child.values) - 1
        return complexity

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        complexity = self._compute_complexity(node)
        if complexity > self.threshold:
            self.violations.append(
                ComplexityViolation(
                    filepath=self._filepath,
                    function_name=node.name,
                    lineno=node.lineno,
                    complexity=complexity,
                )
            )
        self.generic_visit(node)

    visit_FunctionDef = _check_function
    visit_AsyncFunctionDef = _check_function


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def _collect_python_files(target: Path) -> List[Path]:
    """Recursively collect .py files under *target*, skipping exempt dirs."""
    files: List[Path] = []
    if not target.is_dir():
        return files
    for py_file in sorted(target.rglob("*.py")):
        if any(exc in py_file.parts for exc in _EXEMPT_DIRS):
            continue
        files.append(py_file)
    return files


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_audit(
    target: Path = _DEFAULT_TARGET,
    threshold: int = _DEFAULT_THRESHOLD,
) -> AuditReport:
    """Run the mirror audit and return an :class:`AuditReport`.

    Args:
        target: Root directory to scan (defaults to ``cortex/``).
        threshold: Maximum allowed cyclomatic complexity per function.

    Returns:
        :class:`AuditReport` with all violations found.
    """
    visitor = _ComplexityVisitor(threshold=threshold)
    report = AuditReport(threshold=threshold)

    for py_file in _collect_python_files(target):
        report.scanned += 1
        report.violations.extend(visitor.audit_file(py_file))

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mirror Audit: enforce cyclomatic complexity limits."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=_DEFAULT_TARGET,
        help="Directory to scan (default: cortex/).",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=_DEFAULT_THRESHOLD,
        help="Max cyclomatic complexity per function (default: 10).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-violation output; only print summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    """CLI entry point. Returns exit code (0 = pass, 1 = violations found)."""
    args = _build_parser().parse_args(argv)
    report = run_audit(target=args.path, threshold=args.threshold)

    if not args.quiet:
        for v in report.violations:
            print(v)  # noqa: T201 — intentional CLI output

    scanned = report.scanned
    n = len(report.violations)
    print(  # noqa: T201
        f"\nMirror Audit: scanned {scanned} files | "
        f"threshold={report.threshold} | violations={n}"
    )
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
