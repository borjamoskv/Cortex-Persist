"""HotStateDB — SQLite-backed hot state for the daemon.

Replaces the in-memory dict+JSON flush pattern with a durable,
queryable, cross-process-safe KV store using SQLite WAL mode.

Features:
    - O(1) key-value get/set with optional TTL
    - SQL queryable for analytics
    - Atomic writes (WAL mode)
    - Cross-process concurrent reads from CLI/API
    - Auto-migration from legacy handoff.json
    - Metrics: uptime, cycle count, last tick

Derivation: Ω₂ (Thermodynamic Law) — measure exergy, not volume.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.daemon.hot_state")

__all__ = ["HotStateDB"]

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS hot_kv (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    ttl_expires TEXT,               -- ISO timestamp or NULL for permanent
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hot_metrics (
    key         TEXT PRIMARY KEY,
    value       REAL NOT NULL DEFAULT 0.0,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hot_kv_ttl ON hot_kv(ttl_expires)
    WHERE ttl_expires IS NOT NULL;
"""

# Default metrics initialized on first boot
_DEFAULT_METRICS = {
    "uptime_start": 0.0,
    "cycle_count": 0.0,
    "total_tasks_run": 0.0,
    "total_events_published": 0.0,
    "last_tick_ms": 0.0,
}


class HotStateDB:
    """SQLite-backed hot state for cross-process daemon state.

    Usage:
        state = HotStateDB()
        state.set("daemon.mode", "active")
        state.set("cache.token", "abc123", ttl_s=3600)

        print(state.get("daemon.mode"))  # "active"
        print(state.metrics())           # {"uptime_s": ..., "cycle_count": ...}
    """

    __slots__ = ("_db_path", "_boot_time")

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".cortex" / "hot_state.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._boot_time = time.monotonic()
        self._init_db()
        self._migrate_legacy()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            # Initialize default metrics
            now = datetime.now(timezone.utc).isoformat()
            for key, val in _DEFAULT_METRICS.items():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO hot_metrics (key, value, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, val, now),
                )
            # Record boot time
            conn.execute(
                """
                UPDATE hot_metrics SET value = ?, updated_at = ?
                WHERE key = 'uptime_start'
                """,
                (time.time(), now),
            )

    def _migrate_legacy(self) -> None:
        """Auto-migrate from legacy handoff.json if it exists."""
        legacy = Path.home() / "cortex" / "handoff.json"
        if not legacy.exists():
            return
        try:
            data = json.loads(legacy.read_text())
            now = datetime.now(timezone.utc).isoformat()
            with self._conn() as conn:
                for key, value in data.items():
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO hot_kv (key, value, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (f"legacy.{key}", json.dumps(value), now, now),
                    )
            logger.info("Migrated %d keys from legacy handoff.json", len(data))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to migrate legacy state: %s", e)

    # ─── KV Operations ────────────────────────────────────────────

    def set(self, key: str, value: Any, ttl_s: float | None = None) -> None:
        """Set or update a key-value pair. Value is JSON-serialized."""
        now = datetime.now(timezone.utc).isoformat()
        ttl_expires = None
        if ttl_s is not None:
            from datetime import timedelta

            ttl_expires = (
                datetime.now(timezone.utc) + timedelta(seconds=ttl_s)
            ).isoformat()

        serialized = json.dumps(value, default=str)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO hot_kv (key, value, ttl_expires, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    ttl_expires = excluded.ttl_expires,
                    updated_at = excluded.updated_at
                """,
                (key, serialized, ttl_expires, now, now),
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key. Returns default if missing or expired."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT value, ttl_expires FROM hot_kv WHERE key = ?
                """,
                (key,),
            ).fetchone()

        if row is None:
            return default

        # Check TTL
        if row["ttl_expires"] and row["ttl_expires"] < now:
            self.delete(key)
            return default

        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if it existed."""
        with self._conn() as conn:
            result = conn.execute("DELETE FROM hot_kv WHERE key = ?", (key,))
        return result.rowcount > 0

    def keys(self, prefix: str = "") -> list[str]:
        """List all keys matching a prefix."""
        with self._conn() as conn:
            if prefix:
                rows = conn.execute(
                    "SELECT key FROM hot_kv WHERE key LIKE ?",
                    (f"{prefix}%",),
                ).fetchall()
            else:
                rows = conn.execute("SELECT key FROM hot_kv").fetchall()
        return [r["key"] for r in rows]

    def purge_expired(self) -> int:
        """Remove all expired keys. Returns count removed."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            result = conn.execute(
                "DELETE FROM hot_kv WHERE ttl_expires IS NOT NULL AND ttl_expires < ?",
                (now,),
            )
        count = result.rowcount
        if count:
            logger.debug("Purged %d expired keys", count)
        return count

    # ─── Metrics ──────────────────────────────────────────────────

    def increment(self, metric: str, delta: float = 1.0) -> float:
        """Atomically increment a metric counter. Returns new value."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO hot_metrics (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = value + excluded.value,
                    updated_at = excluded.updated_at
                """,
                (metric, delta, now),
            )
            row = conn.execute(
                "SELECT value FROM hot_metrics WHERE key = ?", (metric,)
            ).fetchone()
        return row["value"] if row else delta

    def set_metric(self, metric: str, value: float) -> None:
        """Set a metric to an absolute value."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO hot_metrics (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (metric, value, now),
            )

    def metrics(self) -> dict[str, Any]:
        """Return all metrics as a dict with computed uptime."""
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM hot_metrics").fetchall()
        result = {r["key"]: r["value"] for r in rows}

        # Compute live uptime
        boot = result.get("uptime_start", 0)
        if boot > 0:
            result["uptime_s"] = round(time.time() - boot, 1)

        return result

    # ─── Query & Export ───────────────────────────────────────────

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute arbitrary SQL against the hot state. Read-only recommended."""
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def export_snapshot(self) -> dict[str, Any]:
        """Full state dump for debugging/dashboards."""
        with self._conn() as conn:
            kv_rows = conn.execute(
                "SELECT key, value, ttl_expires, updated_at FROM hot_kv"
            ).fetchall()
            metric_rows = conn.execute(
                "SELECT key, value FROM hot_metrics"
            ).fetchall()

        return {
            "kv": {r["key"]: json.loads(r["value"]) for r in kv_rows},
            "metrics": {r["key"]: r["value"] for r in metric_rows},
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "db_path": str(self._db_path),
        }

    def __len__(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM hot_kv").fetchone()
        return row["c"] if row else 0
