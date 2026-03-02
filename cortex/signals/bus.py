# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v6.0 — Persistent Signal Bus (L1 Consciousness Layer).

SQLite-backed signal persistence that survives process boundaries.
Tools emit signals; other tools poll/subscribe to react.

Architecture:
    ┌─────────────────────────────────────────────┐
    │              CORTEX SIGNAL BUS              │
    │  (SQLite WAL — 0 external dependencies)     │
    ├─────────────────────────────────────────────┤
    │  emit("plan:done", {project, files})        │
    │  emit("error:critical", {trace, context})   │
    │  emit("bridge:detected", {from, to})        │
    │  emit("build:result", {status, metrics})    │
    │                                             │
    │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐       │
    │  │arki │  │legi │  │velo │  │tram │  ...   │
    │  │tetv │  │on   │  │citv │  │polin│        │
    │  └──┬──┘  └──┬──┘  └──┬──┘  └──┬──┘       │
    │     └────────┴────────┴────────┘            │
    │          subscribe / poll                   │
    └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta

from cortex.signals.models import Signal, signal_from_row

__all__ = ["SignalBus"]

logger = logging.getLogger("cortex.signals.bus")

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL,
    project     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    consumed_by TEXT NOT NULL DEFAULT '[]'
);
"""

_CREATE_INDEXES = """\
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
"""


class SignalBus:
    """Persistent signal bus backed by SQLite.

    Sync-first design (matches CLI usage pattern). For async contexts,
    wrap calls with `asyncio.to_thread()` or use the existing
    `DistributedEventBus` with the persistence bridge.

    Args:
        conn: A sqlite3 connection (from `cortex.engine` or standalone).
    """

    __slots__ = ("_conn", "_ready")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ready = False

    def ensure_table(self) -> None:
        """Create the signals table if it doesn't exist (idempotent)."""
        if self._ready:
            return
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
        self._conn.commit()
        self._ready = True

    # ── Emit ─────────────────────────────────────────────────────────

    def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        source: str = "cli",
        project: str | None = None,
    ) -> int:
        """Persist a signal. Returns the signal ID.

        Args:
            event_type: Dotted event name (e.g. 'plan:done', 'error:critical').
            payload: Arbitrary JSON-serializable data.
            source: Emitter identity (e.g. 'arkitetv-1', 'agent:gemini').
            project: Optional project scope.

        Returns:
            The auto-generated signal ID.
        """
        self.ensure_table()
        cursor = self._conn.execute(
            """INSERT INTO signals (event_type, payload, source, project)
               VALUES (?, ?, ?, ?)""",
            (
                event_type,
                json.dumps(payload or {}, default=str),
                source,
                project,
            ),
        )
        self._conn.commit()
        signal_id = cursor.lastrowid
        logger.info(
            "Signal emitted: %s (#%d) from %s",
            event_type,
            signal_id,
            source,
        )
        return signal_id  # type: ignore[reportReturnType]

    # ── Poll (consume) ───────────────────────────────────────────────

    def poll(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        """Fetch unconsumed signals and mark them as consumed.

        This is an atomic read-and-mark operation: each signal is only
        delivered once per consumer.

        Args:
            event_type: Filter by event type.
            source: Filter by emitter.
            project: Filter by project.
            consumer: Identity of the consuming tool/agent.
            limit: Maximum signals to return.

        Returns:
            List of Signal objects that were newly consumed.
        """
        self.ensure_table()
        signals = self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

        # Mark as consumed atomically
        for sig in signals:
            new_consumed = sig.consumed_by + [consumer]
            self._conn.execute(
                "UPDATE signals SET consumed_by = ? WHERE id = ?",
                (json.dumps(new_consumed), sig.id),
            )
        if signals:
            self._conn.commit()
            logger.info(
                "Polled %d signal(s) as consumer '%s'",
                len(signals),
                consumer,
            )

        return signals

    # ── Peek (no consume) ────────────────────────────────────────────

    def peek(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        consumer: str | None = None,
        limit: int = 50,
    ) -> list[Signal]:
        """Fetch signals without consuming them.

        If consumer is specified, only shows signals not yet consumed
        by that consumer.
        """
        self.ensure_table()
        return self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

    # ── History ──────────────────────────────────────────────────────

    def history(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[Signal]:
        """Query all signals (including consumed), newest first."""
        self.ensure_table()
        query = (
            "SELECT id, event_type, payload, source, project,"
            " created_at, consumed_by FROM signals WHERE 1=1"
        )
        params: list = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source:
            query += " AND source = ?"
            params.append(source)
        if project:
            query += " AND project = ?"
            params.append(project)
        if since:
            query += " AND created_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [signal_from_row(row) for row in cursor.fetchall()]

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Aggregate signal statistics.

        Returns:
            Dict with total, by_type, by_source, unconsumed counts.
        """
        self.ensure_table()
        result: dict = {}

        # Total count
        row = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()
        result["total"] = row[0] if row else 0

        # By type
        cursor = self._conn.execute(
            "SELECT event_type, COUNT(*) FROM signals GROUP BY event_type ORDER BY COUNT(*) DESC"
        )
        result["by_type"] = {r[0]: r[1] for r in cursor.fetchall()}

        # By source
        cursor = self._conn.execute(
            "SELECT source, COUNT(*) FROM signals GROUP BY source ORDER BY COUNT(*) DESC"
        )
        result["by_source"] = {r[0]: r[1] for r in cursor.fetchall()}

        # Unconsumed (consumed_by == '[]')
        row = self._conn.execute("SELECT COUNT(*) FROM signals WHERE consumed_by = '[]'").fetchone()
        result["unconsumed"] = row[0] if row else 0

        return result

    # ── Garbage Collection ──────────────────────────────────────────

    def gc(self, max_age_days: int = 30) -> int:
        """Prune consumed signals older than threshold.

        Only deletes signals that have been consumed by at least one
        consumer. Unconsumed signals are never garbage collected.

        Args:
            max_age_days: Age threshold in days.

        Returns:
            Number of signals pruned.
        """
        self.ensure_table()
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        cursor = self._conn.execute(
            """DELETE FROM signals
               WHERE consumed_by != '[]'
               AND created_at < ?""",
            (cutoff,),
        )
        self._conn.commit()
        pruned = cursor.rowcount
        if pruned:
            logger.info("GC: pruned %d consumed signal(s) older than %d days", pruned, max_age_days)
        return pruned

    # ── Internal Query Builder ──────────────────────────────────────

    def _query(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        unconsumed_by: str | None = None,
        limit: int = 50,
    ) -> list[Signal]:
        """Build and execute a filtered query."""
        query = (
            "SELECT id, event_type, payload, source, project,"
            " created_at, consumed_by FROM signals WHERE 1=1"
        )
        params: list = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source:
            query += " AND source = ?"
            params.append(source)
        if project:
            query += " AND project = ?"
            params.append(project)
        if unconsumed_by:
            # JSON array does NOT contain the consumer string
            query += " AND consumed_by NOT LIKE ?"
            params.append(f'%"{unconsumed_by}"%')

        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [signal_from_row(row) for row in cursor.fetchall()]
