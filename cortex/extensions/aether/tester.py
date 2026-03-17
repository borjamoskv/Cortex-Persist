"""MOSKV-Aether — Tester Agent.

Detects test framework and runs tests in the repo.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cortex.extensions.aether.models import TesterOutput
from cortex.extensions.aether.tools import AgentToolkit

__all__ = ["TesterAgent"]

logger = logging.getLogger("cortex.extensions.aether.tester")


def _detect_test_command(repo_path: Path) -> str:
    """Auto-detect the appropriate test command for the repo."""
    if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
        return "python -m pytest -q --tb=short 2>&1 | head -80"
    if (repo_path / "package.json").exists():
        return "npm test -- --passWithNoTests 2>&1 | head -80"
    if (repo_path / "Cargo.toml").exists():
        return "cargo test 2>&1 | head -80"
    if (repo_path / "go.mod").exists():
        return "go test ./... 2>&1 | head -80"
    if (repo_path / "Makefile").exists():
        return "make test 2>&1 | head -80"
    return "echo 'No test command detected — skipping tests'"


class TesterAgent:
    """Runs the project's test suite and reports pass/fail."""

    def run(self, toolkit: AgentToolkit) -> TesterOutput:
        """Run tests and return structured output."""
        cmd = _detect_test_command(toolkit.repo_path)
        logger.info("🧪 Running: %s", cmd)

        output = toolkit.bash(cmd, timeout=120)
        passed = self._infer_pass(output, cmd)

        logger.info("🧪 Tests %s", "PASSED ✅" if passed else "FAILED ❌")
        return TesterOutput(passed=passed, output=output, command=cmd)

    @staticmethod
    def _infer_pass(output: str, cmd: str) -> bool:
        """Heuristically determine if tests passed from output."""
        lower = output.lower()

        # Pytest
        if "passed" in lower and "failed" not in lower and "error" not in lower:
            return True
        if "no tests ran" in lower or "no test" in lower:
            return True  # no tests = no failure from Aether's perspective

        # npm / jest
        if "tests failed" in lower or "test suites failed" in lower:
            return False
        if "tests passed" in lower or "test suites passed" in lower:
            return True

        # Cargo
        if "test result: ok" in lower:
            return True
        if "test result: failed" in lower:
            return False

        # Go
        if "--- fail" in lower:
            return False
        if "ok  \t" in lower:
            return True

        # Generic: no tests detected
        if "no test" in lower or "skip" in lower:
            return True

        # Fallback: no explicit failure keywords
        no_fail_tokens = ("error", "fail", "exception", "traceback")
        return not any(t in lower for t in no_fail_tokens)
