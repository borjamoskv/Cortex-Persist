"""
Rollback Spine (α₁ Guard-as-a-Service)

Handles automatic snapshots before risky operations.
- Dependency changes -> Git stash
- Migrations -> SQLite backup
"""

import logging
import subprocess
import shutil
from pathlib import Path
from cortex.utils.canonical import now_iso

logger = logging.getLogger("cortex.daemon.rollback")


class RollbackSpine:
    """Manages system snapshots before risky operations."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else None
        self.snapshots_dir = Path.home() / ".cortex" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def snapshot_git(self, reason: str) -> str | None:
        """Create a git stash of current changes as a rollback point."""
        try:
            # Check if inside a git repo
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
            )

            stash_msg = f"CORTEX-GUARD-SNAPSHOT: {reason} at {now_iso()}"
            result = subprocess.run(  # noqa: S603
                ["git", "stash", "push", "-m", stash_msg],
                capture_output=True,
                text=True,  # noqa: S607
            )
            if "No local changes to save" not in result.stdout:
                logger.info(f"Created Git snapshot: {stash_msg}")
                return stash_msg
            return None
        except subprocess.CalledProcessError:
            logger.debug("Not in a git repository or git error occurred.")
            return None

    def snapshot_sqlite(self, reason: str) -> str | None:
        """Create a backup of the main SQLite database."""
        if not self.db_path or not self.db_path.exists():
            return None

        timestamp = now_iso().replace(":", "").replace("-", "")
        backup_path = self.snapshots_dir / f"{self.db_path.stem}_{timestamp}.sqlite"

        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Created SQLite snapshot at {backup_path} for {reason}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create SQLite snapshot: {e}")
            return None

    def create_snapshot(self, action_type: str, reason: str) -> dict:
        """Route to appropriate snapshot mechanism based on action_type."""
        snapshot_refs = {}
        if action_type == "dep_change":
            ref = self.snapshot_git(reason)
            if ref:
                snapshot_refs["git_stash"] = ref
        elif action_type == "migration":
            ref = self.snapshot_sqlite(reason)
            if ref:
                snapshot_refs["sqlite_backup"] = ref

        return snapshot_refs
