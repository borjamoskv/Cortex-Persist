"""Utilities for MEJORAlo engine."""

import subprocess
from pathlib import Path

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
    }
    return cmds.get(stack)


def get_lint_cmd(stack: str) -> list[str] | None:
    cmds = {
        "node": ["npm", "run", "lint"],
        "python": ["ruff", "check", "."],
    }
    return cmds.get(stack)


def get_test_cmd(stack: str) -> list[str] | None:
    cmds = {
        "node": ["npm", "test"],
        "python": ["pytest"],
    }
    return cmds.get(stack)


def run_quiet(cmd: list[str], cwd: str | Path) -> bool:
    """Run a command suppressed, return True if exit code 0."""
    try:
        subprocess.check_call(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
