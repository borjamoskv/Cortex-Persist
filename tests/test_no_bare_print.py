"""AST-based lint test: zero bare print() calls in production code.

Verifies that modules in cortex/engine/, cortex/memory/,
cortex/guards/, and cortex/core/ use logging instead of raw print().

Bare print() in the CLI layer (cortex/cli/) is intentional and exempt.
Print inside docstrings or string literals is not flagged.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

# ---------------------------------------------------------------------------
# Directories to audit (relative to repo root)
# ---------------------------------------------------------------------------

# Start search from repo root; tests run from the root by default.
_REPO_ROOT = Path(__file__).parent.parent

_AUDITED_DIRS: list[str] = [
    "cortex/engine",
    "cortex/memory",
    "cortex/guards",
    "cortex/core",
    "cortex/agents",
    "cortex/database",
]

# Directories we NEVER flag (intentional Rich/print output)
_EXEMPT_DIRS: frozenset[str] = frozenset({"cli", "__pycache__", ".venv"})


# ---------------------------------------------------------------------------
# Violation record
# ---------------------------------------------------------------------------


class PrintViolation(NamedTuple):
    path: str
    lineno: int
    col: int
    source_line: str


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


def _find_bare_prints(source: str, filepath: str) -> list[PrintViolation]:
    """Return all bare print() call-statement nodes in *source*.

    A call is "bare" when:
    - The function being called is the builtin `print` (Name node, id=='print')
    - It appears as a top-level expression statement (Expr node)
    - It is NOT inside a docstring / comment (those don't appear in the AST)
    """
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []  # Let the interpreter surface syntax errors elsewhere

    violations: list[PrintViolation] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if isinstance(func, ast.Name) and func.id == "print":
            lineno = node.lineno
            col = node.col_offset
            raw = source_lines[lineno - 1].strip() if lineno <= len(source_lines) else ""
            violations.append(PrintViolation(filepath, lineno, col, raw))

    return violations


# ---------------------------------------------------------------------------
# Collect files under audit
# ---------------------------------------------------------------------------


def _collect_python_files() -> list[Path]:
    """Return sorted list of .py files in the audited directories."""
    files: list[Path] = []
    for dir_rel in _AUDITED_DIRS:
        target = _REPO_ROOT / dir_rel
        if not target.is_dir():
            continue  # Directory doesn't exist yet — skip gracefully
        for py_file in sorted(target.rglob("*.py")):
            if any(exc in py_file.parts for exc in _EXEMPT_DIRS):
                continue
            files.append(py_file)
    return files


# ---------------------------------------------------------------------------
# Parametric test
# ---------------------------------------------------------------------------

_ALL_FILES = _collect_python_files()


@pytest.mark.parametrize(
    "py_file",
    _ALL_FILES,
    ids=[str(p.relative_to(_REPO_ROOT)) for p in _ALL_FILES],
)
def test_no_bare_print_in_production_code(py_file: Path) -> None:
    """Assert that *py_file* contains no bare print() expression statements."""
    source = py_file.read_text(encoding="utf-8", errors="replace")
    violations = _find_bare_prints(source, str(py_file))

    if violations:
        lines = "\n".join(
            f"  line {v.lineno}: {v.source_line}" for v in violations
        )
        pytest.fail(
            f"{py_file.relative_to(_REPO_ROOT)} contains {len(violations)} "
            f"bare print() call(s):\n{lines}\n"
            "Replace with logging.getLogger(__name__).info/warning/error()."
        )


# ---------------------------------------------------------------------------
# Sanity: the audited dirs list must resolve to at least one file
# ---------------------------------------------------------------------------


def test_audit_covers_at_least_one_file() -> None:
    """Ensure the test discovery found at least one Python file to audit."""
    assert len(_ALL_FILES) > 0, (
        f"No Python files found under {_AUDITED_DIRS!r} relative to {_REPO_ROOT}. "
        "Check that _AUDITED_DIRS paths are correct."
    )
