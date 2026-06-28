# [C5-REAL] Exergy-Maximized
"""
OSYNC Guard - Enforces consistency boundaries during workspace synchronization.
Ensures Lamport clock sequencing, Nexus symlinks, and repository alignment.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("cortex.guards.osync")


class OSYNCViolationError(Exception):
    """Raised when an OSYNC synchronization policy is violated."""
    pass


class OSYNCGuard:
    """Enforces OSYNC-001 to OSYNC-050 synchronization rules."""

    @classmethod
    def verify_nexus_symlink(cls, link_path: Path, expected_target: Path) -> None:
        """
        INV-OSYNC-012: Asserts that a Nexus bridging node is a valid symlink 
        pointing to the expected target.
        """
        if not link_path.is_symlink():
            logger.error("[P0] OSYNCGuard: Path %s is not a symlink.", link_path)
            raise OSYNCViolationError(f"Nexus Invariant Broken: {link_path} must be a symlink.")

        real_target = Path(os.readlink(link_path)).resolve()
        resolved_expected = expected_target.resolve()
        
        if real_target != resolved_expected:
            logger.error(
                "[P0] OSYNCGuard: Symlink target mismatch. Found %s, expected %s",
                real_target, resolved_expected
            )
            raise OSYNCViolationError("Nexus Target Drift: Symlink points to divergent codebase.")

    @classmethod
    def verify_git_clean(cls, repo_path: Path) -> None:
        """
        INV-OSYNC-008: Asserts that the working tree has no uncommitted changes 
        before syncing.
        """
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            if res.stdout.strip():
                logger.error("[P0] OSYNCGuard: Working tree is dirty at %s.", repo_path)
                raise OSYNCViolationError("Sync Denied: Working tree contains uncommitted state changes.")
        except subprocess.CalledProcessError as e:
            raise OSYNCViolationError("Git execution failure during status validation.") from e

    @classmethod
    def verify_lamport_ordering(cls, local_clock: int, remote_clock: int) -> int:
        """
        INV-OSYNC-044: Enforces Lamport clock synchronization.
        Returns the updated logical time.
        """
        if remote_clock < 0 or local_clock < 0:
            raise OSYNCViolationError("Logical time counters must be non-negative integers.")
        
        # Clock updates to max(local, remote) + 1
        return max(local_clock, remote_clock) + 1
