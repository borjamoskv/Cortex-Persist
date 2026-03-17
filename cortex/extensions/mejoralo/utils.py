"""Utilities for MEJORAlo engine."""

<<<<<<< HEAD
import logging
from pathlib import Path

from cortex.guards.path_guard import is_safe_path
=======
import subprocess
from pathlib import Path
from typing import Any, Optional

>>>>>>> origin/main
from .constants import STACK_MARKERS

__all__ = [
    "detect_stack",
    "get_build_cmd",
    "get_lint_cmd",
    "get_test_cmd",
    "run_quiet",
]

<<<<<<< HEAD
logger = logging.getLogger("cortex.extensions.mejoralo.utils")


def detect_stack(path: str | Path) -> str:
    """Detect project stack from marker files."""
    if not is_safe_path(path):
        return "unknown"
    try:
        target = Path(path).expanduser().resolve()
        if not target.is_dir():
            return "unknown"
    except (ValueError, OSError):
        return "unknown"

    for stack, marker in STACK_MARKERS.items():
        if (target / marker).exists():
=======

def detect_stack(path: str | Path) -> str:
    """Detect project stack from marker files."""
    p = Path(path)
    for stack, marker in STACK_MARKERS.items():
        if (p / marker).exists():
>>>>>>> origin/main
            return stack
    return "unknown"


<<<<<<< HEAD
def get_build_cmd(stack: str) -> list[str] | None:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
=======
def get_build_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
        "swift": ["swift", "build"],
>>>>>>> origin/main
    }
    return cmds.get(stack)


<<<<<<< HEAD
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
=======
def get_test_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "test"],
        "python": ["python", "-m", "pytest", "--tb=no", "-q"],
        "swift": ["swift", "test"],
>>>>>>> origin/main
    }
    return cmds.get(stack)


<<<<<<< HEAD
def run_quiet(cmd: list[str]) -> tuple[int, str, str]:
    """Run command without noise. Enforces path validation."""
    from cortex.core.paths import is_safe_path
    if not cmd or not is_safe_path(cmd[0]):
        msg = f"Prohibida la ejecución de comando inseguro: {cmd[0] if cmd else 'None'}"
        raise ValueError(msg)

    import subprocess  # nosec B404
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )  # nosec B603
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr
=======
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
>>>>>>> origin/main
