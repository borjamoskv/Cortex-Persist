import asyncio
import json
import logging
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite

from cortex.config import DEFAULT_DB_PATH

__all__ = ["SnapshotRecord", "SnapshotManager"]

logger = logging.getLogger("cortex")


def _write_snapshot_meta(meta_path: Path, record: dict) -> None:
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)


def _read_snapshot_meta(meta_file: Path) -> dict:
    with open(meta_file, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class SnapshotRecord:
    """Metadata for a CORTEX snapshot."""

    id: int
    name: str
    path: str
    tx_id: int
    merkle_root: str
    created_at: str
    size_mb: float


def _parse_snapshot_meta(meta_file: Path) -> SnapshotRecord | None:
    try:
        data = _read_snapshot_meta(meta_file)
        db_file = Path(data["path"])
        if db_file.exists():
            return SnapshotRecord(
                id=0,
                name=data["name"],
                path=data.get("path", ""),
                tx_id=data.get("tx_id", 0),
                merkle_root=data.get("merkle_root", ""),
                created_at=data.get("created_at", ""),
                size_mb=data.get("size_mb", 0.0),
            )
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Failed to load snapshot metadata from %s: %s", meta_file, e)
    return None


def _list_snapshots_sync(snapshot_dir: Path) -> list[SnapshotRecord]:
    snapshots = []
    for meta_file in snapshot_dir.glob("*.json"):
        record = _parse_snapshot_meta(meta_file)
        if record:
            snapshots.append(record)
    return sorted(snapshots, key=lambda s: s.created_at, reverse=True)


def _restore_db_files_sync(snap_path: Path, target_path: Path) -> bool:
    backup_path = target_path.with_suffix(".db.bak")
    shutil.copy2(target_path, backup_path)
    try:
        shutil.copy2(snap_path, target_path)
        for wal_file in target_path.parent.glob(f"{target_path.name}-*"):
            wal_file.unlink()
        return True
    except (OSError, ValueError) as e:
        logger.error("Failed to restore snapshot: %s", e)
        shutil.copy2(backup_path, target_path)
        return False


class SnapshotManager:
    """
    Manages physical and logical snapshots of the CORTEX database.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path).expanduser()
        self.snapshot_dir = self.db_path.parent / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    async def create_snapshot(self, name: str, tx_id: int, merkle_root: str) -> SnapshotRecord:
        """Create a consistent physical snapshot of the current database.

        Args:
            name: Descriptive name for the snapshot.
            tx_id: The latest transaction ID included in this snapshot.
            merkle_root: The Merkle Root of the ledger at this point.

        Returns:
            SnapshotRecord containing metadata.
        """
        # Sanitize name to prevent path traversal or malicious filenames
        # Allow only alphanumeric, underscores, and dashes
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cortex_snap_{ts}_{safe_name}.db"
        dest_path = self.snapshot_dir / filename

        # Use VACUUM INTO for a consistent backup of a live database in WAL mode
        async with aiosqlite.connect(str(self.db_path)) as conn:
            try:
                # SQLite doesn't support parameters for VACUUM INTO.
                # Since we sanitized 'name' and we control 'snapshot_dir',
                # this is now safe from injection.
                safe_path = str(dest_path).replace("'", "''")
                await conn.execute(f"VACUUM INTO '{safe_path}'")
                logger.info("Snapshot created via VACUUM INTO: %s", dest_path)
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.error("Snapshot creation failed: %s", e)
                raise

        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)

        # We record the metadata in a alongside JSON file
        meta_path = dest_path.with_suffix(".json")
        record = {
            "name": safe_name,
            "tx_id": tx_id,
            "merkle_root": merkle_root,
            "created_at": datetime.now().isoformat(),
            "size_mb": size_mb,
            "path": str(dest_path),
        }

        # Using run_in_executor to avoid blocking the event loop for file I/O
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _write_snapshot_meta, meta_path, record)

        return SnapshotRecord(
            id=0,  # Metadata ID
            name=safe_name,
            path=str(dest_path),
            tx_id=tx_id,
            merkle_root=merkle_root,
            created_at=record["created_at"],
            size_mb=size_mb,
        )

    async def list_snapshots(self) -> list[SnapshotRecord]:
        """List all available snapshots in the snapshot directory."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _list_snapshots_sync, self.snapshot_dir)

    async def restore_snapshot(self, tx_id: int) -> bool:
        """Restore the database to a specific snapshot state.

        WARNING: This overwrites the current database.
        """
        all_snapshots = await self.list_snapshots()
        snapshots = [s for s in all_snapshots if s.tx_id == tx_id]
        if not snapshots:
            logger.error("No snapshot found for TX %d", tx_id)
            return False

        snap = snapshots[0]
        logger.info("Restoring snapshot from %s", snap.path)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, _restore_db_files_sync, Path(snap.path), self.db_path
        )
