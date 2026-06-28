# [C5-REAL] Exergy-Maximized
"""Git Context Guard - Prevents operations in the wrong repository clone.

This guard enforces MIT-1 (Path Verification) and prevents Sensor Drift
by asserting that the active repository context matches the expected remote
origin before allowing state mutations or diagnostic sweeps.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

LOG = logging.getLogger("cortex.guards.git_context_guard")


class GitContextDriftError(Exception):
    """Raised when the git context does not match the expected topology."""

    pass


class GitContextGuard:
    """Ensures the executing process is within the correct Git tree topology."""

    @staticmethod
    def verify_remote_origin(expected_origin_fragment: str, repo_path: Path | None = None) -> bool:
        """
        Verify that the git repository has a remote origin containing the expected fragment.
        Example fragment: 'borjamoskv/Cortex-Persist'
        """
        cwd = repo_path or Path.cwd()
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            origin_url = result.stdout.strip()

            if expected_origin_fragment not in origin_url:
                LOG.error(
                    "❌ [GIT_CONTEXT_GUARD] Context drift detected. "
                    "Expected origin fragment '%s' not found in '%s'. CWD: %s",
                    expected_origin_fragment,
                    origin_url,
                    cwd,
                )
                raise GitContextDriftError(
                    f"Sensor Drift: Active repository ({origin_url}) does not match expected topology."
                )
            return True

        except subprocess.CalledProcessError as e:
            LOG.error("❌ [GIT_CONTEXT_GUARD] Failed to execute git. Not a git repository? %s", e)
            raise GitContextDriftError("Execution context is not a valid git repository.") from e
        except FileNotFoundError as e:
            LOG.error("❌ [GIT_CONTEXT_GUARD] git executable not found. %s", e)
            raise GitContextDriftError("Git executable missing from environment.") from e
