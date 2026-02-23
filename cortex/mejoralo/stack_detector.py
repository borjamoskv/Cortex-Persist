"""Advanced stack detection with tool intelligence for MEJORAlo."""

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cortex.mejoralo")


@dataclass
class StackIntelligence:
    """Tool commands available for a detected project stack."""

    stack: str
    linter_cmd: str | None
    complexity_cmd: str | None
    security_cmd: str | None
    build_cmd: str | None


_STACK_CONFIGS: dict[str, dict[str, str | None]] = {
    "node": {
        "linter_cmd": "npx eslint . --format=json",
        "complexity_cmd": "npx eslint . --no-eslintrc --plugin complexity --rule 'complexity: [2, 10]'",
        "security_cmd": "npm audit --json",
        "build_cmd": "npx tsc --noEmit",
    },
    "python": {
        "linter_cmd": "ruff check . --output-format=json",
        "complexity_cmd": "radon cc . -a -nc -j",
        "security_cmd": "bandit -r . -f json",
        "build_cmd": "pytest -q --co",
    },
    "rust": {
        "linter_cmd": "cargo clippy --message-format=json",
        "complexity_cmd": None,
        "security_cmd": "cargo audit -q --json",
        "build_cmd": "cargo check --message-format=json",
    },
    "go": {
        "linter_cmd": "golangci-lint run --out-format=json",
        "complexity_cmd": "gocyclo -top 10 .",
        "security_cmd": "gosec -fmt=json ./...",
        "build_cmd": "go test -run=^$ ./...",
    },
}

_MARKER_FILES: dict[str, list[str]] = {
    "node": ["package.json"],
    "python": ["pyproject.toml", "requirements.txt", "setup.py"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
}


def get_stack_intelligence(path: Path) -> StackIntelligence:
    """Detect the project stack and return its tool configuration."""
    resolved = path.resolve()

    for stack, markers in _MARKER_FILES.items():
        if any((resolved / m).exists() for m in markers):
            config = _STACK_CONFIGS[stack]
            return StackIntelligence(stack=stack, **config)  # type: ignore[arg-type]

    return StackIntelligence(
        stack="unknown",
        linter_cmd=None,
        complexity_cmd=None,
        security_cmd=None,
        build_cmd=None,
    )


def run_cmd(cmd: str | None, cwd: Path) -> tuple[int, str]:
    """Execute a shell command safely, returning (returncode, combined_output)."""
    if not cmd:
        return (0, "")
    try:
        result = subprocess.run(
            shlex.split(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return (result.returncode, result.stdout + result.stderr)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        logger.warning("Failed to execute %r in %s", cmd, cwd, exc_info=True)
        return (-1, "")
