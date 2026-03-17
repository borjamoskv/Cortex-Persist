"""
Sovereign Synchronization (Axiom Ω₂: Entropic Asymmetry).

Lock mechanism using append-only intent ledger.

Architecture:
- acquire(): atomic INSERT intent + promote (single BEGIN IMMEDIATE),
  then read-only poll with constant 50ms sleep.
- release(): atomic evict + promote next (single BEGIN IMMEDIATE).
- Polling is READ-ONLY — zero write contention during wait.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.lock")

_POLL_INTERVAL = 0.05  # 50ms — tight enough for throughput


class SovereignLock:
    """Sovereign Lock: append-only intent ledger with state projection."""

    def __init__(self, engine: Any):
        self._engine = engine
        self._db_path = getattr(engine, "db_path", None) or getattr(engine, "_db_path", None)

    @asynccontextmanager
    async def _conn(self):
        """Dedicated aiosqlite connection (WAL mode, 10s busy timeout)."""
        import aiosqlite

        db_path = str(self._db_path or getattr(self._engine, "_db_path", None))
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=10000")
            yield conn

    # ─── Public API ────────────────────────────────────────────────────

    async def acquire(
        self,
        resource: str,
        agent_id: str,
        timeout_s: float = 10.0,
        ttl_s: float = 30.0,
        priority: int = 0,
    ) -> bool:
        """Insert intent + initial promote, then read-only poll."""
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()

        # 1. Atomic: insert intent + try to promote (single writer txn)
        async with self._conn() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            await conn.execute(
                "INSERT INTO lock_intents "
                "(resource, agent_id, action, priority, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (resource, agent_id, "request", priority, expires_at),
            )
            holder = await self._promote_if_free(conn, resource)
            await conn.commit()

        # Fast path: we got promoted immediately
        if holder == agent_id:
            logger.debug("SovereignLock: %s acquired by %s (fast)", resource, agent_id)
            return True

        # 2. Read-only poll loop (no writes, no contention)
        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)
        while datetime.now(timezone.utc) < deadline:
            await asyncio.sleep(_POLL_INTERVAL)

            async with self._conn() as conn:
                async with conn.execute(
                    "SELECT holder_agent, expires_at " "FROM lock_state WHERE resource = ?",
                    (resource,),
                ) as cur:
                    row = await cur.fetchone()

            if not row:
                # State cleared but not yet promoted — rare race;
                # next release() or acquire() will promote.
                continue

            holder, expiry = row
            if holder == agent_id:
                logger.debug(
                    "SovereignLock: %s acquired by %s",
                    resource,
                    agent_id,
                )
                return True

            # Expired holder → evict and promote atomically
            if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
                async with self._conn() as conn:
                    await conn.execute("BEGIN IMMEDIATE")
                    await self._evict_and_promote(conn, resource)
                    await conn.commit()

        logger.warning(
            "SovereignLock: Timeout acquiring %s for %s",
            resource,
            agent_id,
        )
        return False

    async def release(self, resource: str, agent_id: str):
        """Atomic: remove holder + promote next candidate."""
        async with self._conn() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            # Clean expired intents
            now = datetime.now(timezone.utc).isoformat()
            await conn.execute(
                "DELETE FROM lock_intents " "WHERE expires_at < ? AND action = 'request'",
                (now,),
            )
            # Remove all intents from this agent for this resource
            await conn.execute(
                "DELETE FROM lock_intents " "WHERE resource = ? AND agent_id = ?",
                (resource, agent_id),
            )
            # Clear current holder
            await conn.execute(
                "DELETE FROM lock_state WHERE resource = ?",
                (resource,),
            )
            # Promote next candidate
            await self._promote_if_free(conn, resource)
            await conn.commit()

        logger.debug("SovereignLock: %s released by %s", resource, agent_id)

    async def is_locked(self, resource: str) -> bool:
        """Read-only state check."""
        async with self._conn() as conn:
            async with conn.execute(
                "SELECT holder_agent, expires_at " "FROM lock_state WHERE resource = ?",
                (resource,),
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return False
        holder, expiry = row
        if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
            return False
        return holder is not None

    # ─── Private ───────────────────────────────────────────────────────

    async def _promote_if_free(self, conn: aiosqlite.Connection, resource: str) -> str | None:
        """If no valid holder exists, promote the top candidate.

        MUST be called inside BEGIN IMMEDIATE. Does NOT commit.
        Returns the current (or newly promoted) holder agent_id.
        """
        async with conn.execute(
            "SELECT holder_agent, expires_at " "FROM lock_state WHERE resource = ?",
            (resource,),
        ) as cur:
            state = await cur.fetchone()

        if state:
            holder, expiry = state
            if holder and (
                not expiry or datetime.fromisoformat(expiry) >= datetime.now(timezone.utc)
            ):
                return holder  # Valid holder, nothing to promote

            # Expired — evict
            await conn.execute(
                "DELETE FROM lock_state WHERE resource = ?",
                (resource,),
            )
            await conn.execute(
                "DELETE FROM lock_intents " "WHERE resource = ? AND agent_id = ?",
                (resource, holder),
            )

        # Pick next candidate (priority DESC, FIFO ASC)
        async with conn.execute(
            "SELECT agent_id, expires_at FROM lock_intents "
            "WHERE resource = ? AND action = 'request' "
            "ORDER BY priority DESC, id ASC LIMIT 1",
            (resource,),
        ) as cur:
            row = await cur.fetchone()

        if row:
            new_holder, new_expiry = row
            now = datetime.now(timezone.utc).isoformat()
            async with conn.execute(
                "SELECT COUNT(*) FROM lock_intents " "WHERE resource = ? AND action = 'request'",
                (resource,),
            ) as cur:
                depth = (await cur.fetchone())[0]
            await conn.execute(
                "INSERT OR REPLACE INTO lock_state "
                "(resource, holder_agent, acquired_at, "
                "expires_at, queue_depth) "
                "VALUES (?, ?, ?, ?, ?)",
                (resource, new_holder, now, new_expiry, depth),
            )
            return new_holder

        return None

    async def _evict_and_promote(self, conn: aiosqlite.Connection, resource: str):
        """Evict expired holder and promote next. Inside BEGIN IMMEDIATE."""
        async with conn.execute(
            "SELECT holder_agent, expires_at " "FROM lock_state WHERE resource = ?",
            (resource,),
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return

        holder, expiry = row
        if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
            await conn.execute(
                "DELETE FROM lock_state WHERE resource = ?",
                (resource,),
            )
            if holder:
                await conn.execute(
                    "DELETE FROM lock_intents " "WHERE resource = ? AND agent_id = ?",
                    (resource, holder),
                )
            await self._promote_if_free(conn, resource)
