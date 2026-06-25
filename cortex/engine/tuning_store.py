# [C5-REAL] Exergy-Maximized
"""Tuning Persistence - Save and Restore Learned Optimizations (C5-REAL).

Persists L6 Self-Optimizer tunings to a SQLite database so the system
retains its thermodynamic state and learned optimizations across restarts.

Storage format: SQLite3 (C5-REAL thermodynamic persistence).
Location: project_root/.cortex/tunings.db

Reality Level: C5-REAL
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from cortex.database.core import connect

__all__ = ["TuningStore"]

logger = logging.getLogger("cortex.engine.tuning_store")

_DEFAULT_DB = ".cortex/tunings.db"


class TuningStore:
    """Persistent storage for learned parameter optimizations via SQLite.

    Saves tuning decisions and system thermodynamic state to a C5-REAL SQLite DB.
    On startup, loads previous tunings to avoid cold-start re-learning.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.cwd()
        self._db_path = Path(base_dir) / _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with connect(str(self._db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tunings (
                    subsystem TEXT PRIMARY KEY,
                    params JSON,
                    saved_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_data JSON,
                    stats_data JSON,
                    snapshot_at REAL
                )
                """
            )
            conn.commit()

    def save(self, subsystem: str, params: dict[str, Any]) -> Path:
        """Save tuned parameters for a subsystem."""
        with connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT INTO tunings (subsystem, params, saved_at)
                VALUES (?, ?, ?)
                ON CONFLICT(subsystem) DO UPDATE SET
                    params=excluded.params,
                    saved_at=excluded.saved_at
                """,
                (subsystem, json.dumps(params), time.time()),
            )
        logger.debug("[TUNING_STORE] Saved %s to SQLite", subsystem)
        return self._db_path

    def load(self, subsystem: str) -> dict[str, Any] | None:
        """Load tuned parameters for a subsystem. Returns None if not found."""
        with connect(str(self._db_path)) as conn:
            cursor = conn.execute("SELECT params FROM tunings WHERE subsystem = ?", (subsystem,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None
        return None

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all persisted tunings. Returns {subsystem: params}."""
        result = {}
        with connect(str(self._db_path)) as conn:
            cursor = conn.execute("SELECT subsystem, params FROM tunings")
            for row in cursor.fetchall():
                try:
                    params = json.loads(row[1])
                    if params:
                        result[row[0]] = params
                except json.JSONDecodeError:
                    continue
        return result

    def delete(self, subsystem: str) -> bool:
        """Delete persisted tunings for a subsystem."""
        with connect(str(self._db_path)) as conn:
            cursor = conn.execute("DELETE FROM tunings WHERE subsystem = ?", (subsystem,))
            return cursor.rowcount > 0

    def snapshot(
        self,
        all_params: dict[str, dict[str, Any]],
        stats: dict[str, Any] | None = None,
    ) -> Path:
        """Save a complete optimizer state snapshot."""
        with connect(str(self._db_path)) as conn:
            # Save the global snapshot
            conn.execute(
                """
                INSERT INTO snapshots (snapshot_data, stats_data, snapshot_at)
                VALUES (?, ?, ?)
                """,
                (json.dumps(all_params), json.dumps(stats or {}), time.time()),
            )
            # Also update the individual subsystem tunings
            for sub, params in all_params.items():
                conn.execute(
                    """
                    INSERT INTO tunings (subsystem, params, saved_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(subsystem) DO UPDATE SET
                        params=excluded.params,
                        saved_at=excluded.saved_at
                    """,
                    (sub, json.dumps(params), time.time()),
                )
        logger.info("[TUNING_STORE] Snapshot saved: %d subsystems to SQLite", len(all_params))
        return self._db_path

    def load_snapshot(self) -> dict[str, Any] | None:
        """Load the last optimizer snapshot."""
        with connect(str(self._db_path)) as conn:
            cursor = conn.execute(
                "SELECT snapshot_data, stats_data, snapshot_at FROM snapshots ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                try:
                    return {
                        "params": json.loads(row[0]),
                        "stats": json.loads(row[1]),
                        "snapshot_at": row[2],
                        "snapshot_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row[2])),
                    }
                except Exception as exc:
                    logger.warning("Suppressed exception: %s", exc)
        return None

    @property
    def subsystems(self) -> list[str]:
        """List all subsystems with persisted tunings."""
        with connect(str(self._db_path)) as conn:
            cursor = conn.execute("SELECT subsystem FROM tunings")
            return [row[0] for row in cursor.fetchall()]
