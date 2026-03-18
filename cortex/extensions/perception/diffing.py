"""
CORTEX v5.1 — Perception Layer 1.5: Diff Management.

Maintains a shadow state of the workspace to compute line-level diffs
between file system events. Optimized for memory-efficient tracking
of active source files.
"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import Final, Optional

logger = logging.getLogger("cortex.extensions.perception.diffing")

# Maximum size of a file to perform diffing on (100KB default to prevent OOM)
MAX_DIFF_SIZE_BYTES: Final[int] = 100 * 1024
# Maximum number of lines to keep in a diff to avoid token bloat
MAX_DIFF_LINES: Final[int] = 50


class DiffManager:
    """Manages shadow state of active files to produce line-level diffs."""

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root)
        self._shadow: dict[str, list[str]] = {}  # path -> lines

    def update_file(self, path: str, content: Optional[str] = None) -> Optional[str]:
        """
        Update the shadow state and return a unified diff if available.

        If content is None, it reads from the filesystem.
        Returns a string representation of the diff or None if no change or new file.
        """
        p = Path(path)
        if not p.exists() or p.is_dir():
            if path in self._shadow:
                del self._shadow[path]
            return None

        # Check size before reading
        try:
            if p.stat().st_size > MAX_DIFF_SIZE_BYTES:
                logger.debug("Skipping diff for large file: %s", path)
                return None
        except OSError:
            return None

        try:
            if content is None:
                content = p.read_text(encoding="utf-8", errors="replace")

            new_lines = content.splitlines()
        except Exception as e:
            logger.debug("Failed to read file for diffing: %s (%s)", path, e)
            return None

        old_lines = self._shadow.get(path)
        self._shadow[path] = new_lines

        if old_lines is None:
            # New file or first time seeing it
            return None

        if old_lines == new_lines:
            return ""

        # Generate unified diff
        diff_gen = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="a/" + p.name,
            tofile="b/" + p.name,
            lineterm="",
            n=2  # context lines
        )

        diff_list = list(diff_gen)
        if not diff_list:
            return ""

        # Trim diff to avoid context window bloat
        if len(diff_list) > MAX_DIFF_LINES:
            diff_list = diff_list[:MAX_DIFF_LINES] + ["... (diff truncated)"]

        return "\n".join(diff_list)

    def forget_file(self, path: str) -> None:
        """Remove a file from the shadow state."""
        self._shadow.pop(path, None)

    def clear(self) -> None:
        """Clear all shadow state."""
        self._shadow.clear()
