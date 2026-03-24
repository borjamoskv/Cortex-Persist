"""Utilities for MEJORAlo engine."""
import subprocess
from pathlib import Path
from typing import Any, Optional

from .constants import STACK_MARKERS

__all__ = [
    "detect_stack",
    "get_build_cmd",
    "get_lint_cmd",
    "get_test_cmd",
    "run_quiet",
]


def _safe_resolve_path(path: str | Path, base: Path | None = None) -> Path:
    """Resolve and validate a path to prevent directory traversal.

    If a base directory is provided, the resolved path must be within it.
    Raises ValueError if the path escapes the base directory.
    """
    resolved = Path(path).resolve()
    if base is not None:
        base_resolved = base.resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: '{path}' is outside the allowed base directory."
            )
    return resolved


def detect_stack(path: str | Path) -> str:
    """Detect project stack from marker files."""
    p = _safe_resolve_path(path)
    for stack, marker in STACK_MARKERS.items():
        if (p / marker).exists():
            return stack
    return "unknown"


def get_build_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
        "swift": ["swift", "build"],
    }
    return cmds.get(stack)


def get_test_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "test"],
        "python": ["python", "-m", "pytest", "--tb=no", "-q"],
        "swift": ["swift", "test"],
    }
    return cmds.get(stack)


def get_lint_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npx", "eslint", "."],
        "python": ["python", "-m", "ruff", "check", "."],
    }
    return cmds.get(stack)


def run_quiet(cmd: list[str], cwd: str) -> dict[str, Any]:
    """Run a command quietly, capturing output."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=120,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }
