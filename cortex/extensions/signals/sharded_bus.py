"""
Sharded Signal Bus for CORTEX-SWARM-10K.
Eliminates lock contention by routing messages to specific SQLite DB shards
based on hash(sender/receiver) mod NUM_SHARDS.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from cortex.extensions.signals.bus import _CREATE_INDEXES, _CREATE_TABLE, _build_query
from cortex.extensions.signals.models import Signal, signal_from_row

logger = logging.getLogger("cortex.extensions.signals.sharded_bus")

NUM_SHARDS = 16


class ShardedAsyncSignalBus:
    """O(1) Sharded Message Bus avoiding SQLite lock contention."""

    __slots__ = (
        "_base_dir",
        "_shards",
        "_ready",
        "session_emitted",
        "session_errors",
        "num_shards",
    )

    def __init__(self, base_dir: Path | str, num_shards: int = NUM_SHARDS) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._shards: dict[int, aiosqlite.Connection] = {}
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0
        self.num_shards = num_shards

    def _get_shard_index(self, routing_key: str) -> int:
        h = hashlib.sha256(routing_key.encode("utf-8")).hexdigest()
        return int(h, 16) % self.num_shards

    async def initialize(self) -> None:
        """Initialize all shard connections and create tables."""
        if self._ready:
            return

        for i in range(self.num_shards):
            db_path = self._base_dir / f"swarm_shard_{i:03d}.db"
            conn = await aiosqlite.connect(db_path)
            await conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
            await conn.commit()
            self._shards[i] = conn

        self._ready = True

    async def close(self) -> None:
        """Close all shard connections."""
        for conn in self._shards.values():
            await conn.close()
        self._shards.clear()
        self._ready = False

    async def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        source: str = "cli",
        project: str | None = None,
        routing_key: str | None = None,
    ) -> int:
        if not self._ready:
            await self.initialize()

        rkey = routing_key or source
        shard_idx = self._get_shard_index(rkey)
        conn = self._shards[shard_idx]

        try:
            cursor = await conn.execute(
                "INSERT INTO signals (event_type, payload, source, project) VALUES (?, ?, ?, ?)",
                (
                    event_type,
                    json.dumps(payload or {}, default=str),
                    source,
                    project,
                ),
            )
            await conn.commit()
            self.session_emitted += 1
            return cursor.lastrowid or 0
        except Exception:
            self.session_errors += 1
            raise

    async def history(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        routing_key: str | None = None,
    ) -> list[Signal]:
        if not self._ready:
            await self.initialize()

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

        if routing_key:
            shard_idx = self._get_shard_index(routing_key)
            conns = [self._shards[shard_idx]]
        else:
            conns = list(self._shards.values())

        all_signals = []
        for conn in conns:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            all_signals.extend([signal_from_row(tuple(row)) for row in rows])

        all_signals.sort(key=lambda x: x.created_at, reverse=True)
        return all_signals[:limit]

    async def poll(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        consumer: str = "default",
        limit: int = 50,
        routing_key: str | None = None,
    ) -> list[Signal]:
        if not self._ready:
            await self.initialize()

        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

        shard_indices = (
            [self._get_shard_index(routing_key)] if routing_key else range(self.num_shards)
        )

        polled_signals = []

        for idx in shard_indices:
            if len(polled_signals) >= limit:
                break

            conn = self._shards[idx]
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            batch = [signal_from_row(tuple(r)) for r in rows][: limit - len(polled_signals)]

            for sig in batch:
                new_consumed = sig.consumed_by + [consumer]
                await conn.execute(
                    "UPDATE signals SET consumed_by = ? WHERE id = ?",
                    (json.dumps(new_consumed), sig.id),
                )
            if batch:
                await conn.commit()
                polled_signals.extend(batch)

        return polled_signals

    async def gc(self, max_age_days: int = 30) -> int:
        """Shannon Compaction: Auto-purge stale messages across all shards."""
        if not self._ready:
            await self.initialize()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        total_pruned = 0

        for conn in self._shards.values():
            cursor = await conn.execute(
                "DELETE FROM signals WHERE consumed_by != '[]' AND created_at < ?",
                (cutoff,),
            )
            await conn.commit()
            total_pruned += cursor.rowcount

        if total_pruned:
            logger.info(
                "Sharded GC: pruned %d consumed signal(s) older than %d days",
                total_pruned,
                max_age_days,
            )

        return total_pruned
