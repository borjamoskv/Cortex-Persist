"""Utilities for MEJORAlo engine."""

import subprocess
from pathlib import Path
from typing import Any

from .constants import STACK_MARKERS

__all__ = [
    "detect_stack",
    "get_build_cmd",
    "get_lint_cmd",
    "get_test_cmd",
    "run_quiet",
]


def detect_stack(path: str | Path) -> str:
    """Detect project stack from marker files."""
    p = Path(path)
    for stack, marker in STACK_MARKERS.items():
        if (p / marker).exists():
            return stack
    return "unknown"


def get_build_cmd(stack: str) -> list[str] | None:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
        "swift": ["swift", "build"],
    }
    return cmds.get(stack)


def get_test_cmd(stack: str) -> list[str] | None:
    cmds = {
        "node": ["npm", "test"],
        "python": ["python", "-m", "pytest", "--tb=no", "-q"],
        "swift": ["swift", "test"],
    }
    return cmds.get(stack)


def get_lint_cmd(stack: str) -> list[str] | None:
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
