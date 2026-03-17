from __future__ import annotations
from typing import Optional

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

import aiosqlite

from cortex.extensions.signals.models import Signal, signal_from_row

__all__ = ["SignalBus", "AsyncSignalBus"]

logger = logging.getLogger("cortex.extensions.signals.bus")

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL,
    project TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    consumed_by TEXT NOT NULL DEFAULT '[]'
);
"""

_CREATE_INDEXES = """\
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
"""


def _build_query(
    *,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    project: Optional[str] = None,
    unconsumed_by: Optional[str] = None,
    order: str = "ASC",
    limit: int = 50,
) -> tuple[str, list]:
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
        query += " AND consumed_by NOT LIKE ?"
        params.append(f'%"{unconsumed_by}"%')
    query += f" ORDER BY rowid {order} LIMIT ?"
    params.append(limit)
    return query, params


class AsyncSignalBus:
    __slots__ = ("_conn", "_ready", "session_emitted", "session_errors")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0

    async def ensure_table(self) -> None:
        if self._ready:
            return
        await self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
        await self._conn.commit()
        self._ready = True

    async def emit(
        self,
        event_type: str,
        payload: Optional[dict] = None,
        *,
        source: str = "cli",
        project: Optional[str] = None,
    ) -> int:
        try:
            await self.ensure_table()
            cursor = await self._conn.execute(
                """INSERT INTO signals (event_type, payload, source, project)
                   VALUES (?, ?, ?, ?)""",
                (
                    event_type,
                    json.dumps(payload or {}, default=str),
                    source,
                    project,
                ),
            )
            await self._conn.commit()
            self.session_emitted += 1
            return cursor.lastrowid or 0
        except Exception:  # noqa: BLE001
            self.session_errors += 1
            raise

    async def history(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Signal]:
        await self.ensure_table()
        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            order="DESC",
            limit=limit,
        )
        if since:
            query = query.replace(" ORDER BY", " AND created_at >= ? ORDER BY", 1)
            params.insert(-1, since.isoformat())
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [signal_from_row(tuple(row)) for row in rows]

    async def _query(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        unconsumed_by: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=unconsumed_by,
            limit=limit,
        )
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [signal_from_row(tuple(row)) for row in rows]

    async def poll(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        await self.ensure_table()
        signals = await self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

        for sig in signals:
            new_consumed = sig.consumed_by + [consumer]
            await self._conn.execute(
                "UPDATE signals SET consumed_by = ? WHERE id = ?",
                (json.dumps(new_consumed), sig.id),
            )
        if signals:
            await self._conn.commit()

        return signals

    async def peek(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        await self.ensure_table()
        return await self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

    async def stats(self) -> dict:
        await self.ensure_table()
        result: dict = {
            "session_emitted": self.session_emitted,
            "session_errors": self.session_errors,
        }

        row = await (await self._conn.execute("SELECT COUNT(*) FROM signals")).fetchone()
        result["total"] = row[0] if row else 0

        cursor = await self._conn.execute(
            "SELECT event_type, COUNT(*) FROM signals GROUP BY event_type ORDER BY COUNT(*) DESC"
        )
        result["by_type"] = {r[0]: r[1] for r in await cursor.fetchall()}

        cursor = await self._conn.execute(
            "SELECT source, COUNT(*) FROM signals GROUP BY source ORDER BY COUNT(*) DESC"
        )
        result["by_source"] = {r[0]: r[1] for r in await cursor.fetchall()}

        row = await (
            await self._conn.execute("SELECT COUNT(*) FROM signals WHERE consumed_by = '[]'")
        ).fetchone()
        result["unconsumed"] = row[0] if row else 0

        return result

    async def gc(self, max_age_days: int = 30) -> int:
        await self.ensure_table()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        cursor = await self._conn.execute(
            """DELETE FROM signals
               WHERE consumed_by != '[]'
               AND created_at < ?""",
            (cutoff,),
        )
        await self._conn.commit()
        pruned = cursor.rowcount
        if pruned:
            logger.info(
                "GC: pruned %d consumed signal(s) older than %d days",
                pruned,
                max_age_days,
            )
        return pruned


class SignalBus:
    __slots__ = ("_conn", "_ready", "session_emitted", "session_errors")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0

    def ensure_table(self) -> None:
        if self._ready:
            return
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
        self._conn.commit()
        self._ready = True

    def emit(
        self,
        event_type: str,
        payload: Optional[dict] = None,
        *,
        source: str = "cli",
        project: Optional[str] = None,
    ) -> int:
        try:
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
            self.session_emitted += 1
            return signal_id or 0
        except Exception:  # noqa: BLE001
            self.session_errors += 1
            raise

    def poll(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        signals = self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

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

    def peek(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        return self._query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

    def history(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            order="DESC",
            limit=limit,
        )
        if since:
            query = query.replace(" ORDER BY", " AND created_at >= ? ORDER BY", 1)
            params.insert(-1, since.isoformat())
        cursor = self._conn.execute(query, params)
        return [signal_from_row(tuple(row)) for row in cursor.fetchall()]

    def stats(self) -> dict:
        self.ensure_table()
        result: dict = {
            "session_emitted": self.session_emitted,
            "session_errors": self.session_errors,
        }

        row = self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()
        result["total"] = row[0] if row else 0

        cursor = self._conn.execute(
            "SELECT event_type, COUNT(*) FROM signals GROUP BY event_type ORDER BY COUNT(*) DESC"
        )
        result["by_type"] = {r[0]: r[1] for r in cursor.fetchall()}

        cursor = self._conn.execute(
            "SELECT source, COUNT(*) FROM signals GROUP BY source ORDER BY COUNT(*) DESC"
        )
        result["by_source"] = {r[0]: r[1] for r in cursor.fetchall()}

        row = self._conn.execute("SELECT COUNT(*) FROM signals WHERE consumed_by = '[]'").fetchone()
        result["unconsumed"] = row[0] if row else 0

        return result

    def gc(self, max_age_days: int = 30) -> int:
        self.ensure_table()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
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

    def _query(
        self,
        *,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        unconsumed_by: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=unconsumed_by,
            limit=limit,
        )
        cursor = self._conn.execute(query, params)
        return [signal_from_row(tuple(row)) for row in cursor.fetchall()]
