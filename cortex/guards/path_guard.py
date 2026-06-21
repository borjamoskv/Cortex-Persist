# [C5-REAL] Exergy-Maximized
"""Path Security Guard - Path Traversal Prevention.

Ensures all file system access is restricted to the workspace or allowed
directories.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG = logging.getLogger("cortex.guards.path_guard")


def is_safe_path(path: str | Path, base_dir: Path | None = None) -> bool:
    """Check if a path is safe (no traversal outside base_dir)."""
    if not base_dir:
        # Default to current workspace root or the CORTEX environment root
        # Here we use the package root as a safe default if CWD is not set.
        base_dir = Path.cwd().resolve()

    try:
        # Resolve target and ensure it's relative to base_dir
        target = Path(path).expanduser().resolve()
        if not target.is_relative_to(base_dir):
            LOG.warning(
                "🚫 [PATH_GUARD] Blocked path traversal: %s is not relative to %s", target, base_dir
            )
            return False
        return True
    except (OSError, ValueError) as e:
        LOG.error("❌ [PATH_GUARD] Path resolution failed for %s: %s", path, e)
        return False


def resolve_and_verify(path: str | Path, base_dir: Path | None = None) -> Path | None:
    """Resolve a path and verify its safety. Returns Path if safe, else None."""
    if is_safe_path(path, base_dir):
        return Path(path).expanduser().resolve()
    return None
