"""
Sovereign Synchronization (Axiom Ω₂: Entropic Asymmetry).

Implementation of a Lock-Free synchronization mechanism.
Instead of blocking threads/coroutines, agents append their INTENT to a shared ledger.
A projection (lock_state) determines the current truth.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.lock")


class SovereignLock:
    """
    Sovereign Lock mechanism.
    130/100: Zero-friction append-only concurrency.
    """

    def __init__(self, engine: Any):
        self._engine = engine
        self._db_path = getattr(engine, "db_path", None) or getattr(engine, "_db_path", None)

    async def acquire(
        self,
        resource: str,
        agent_id: str,
        timeout_s: float = 10.0,
        ttl_s: float = 30.0,
        priority: int = 0,
    ) -> bool:
        """
        Attempts to acquire a lock by appending a 'request' intent.

        Args:
            resource: The URI or identifier of the resource.
            agent_id: The ID of the agent requesting the lock.
            timeout_s: How long to wait for acquisition before giving up.
            ttl_s: Time-to-live for the lock if not released.
            priority: Higher priority intents take precedence in reduction.
        """
        expires_at = (datetime.now() + timedelta(seconds=ttl_s)).isoformat()

        # 1. Append Intent (Atomic operation in SQLite)
        async with self._engine.session() as conn:
            await conn.execute(
                "INSERT INTO lock_intents (resource, agent_id, action, priority, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (resource, agent_id, "request", priority, expires_at),
            )
            await conn.commit()

            # 2. Trigger immediate localized reduction
            await self._reduce_resource(conn, resource)

            # 3. Wait for state collapse (polling projection)
            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout_s:
                cursor = await conn.execute(
                    "SELECT holder_agent, expires_at FROM lock_state WHERE resource = ?",
                    (resource,),
                )
                row = await cursor.fetchone()
                if row:
                    holder, expiry = row
                    # Clean up if expired
                    if expiry and datetime.fromisoformat(expiry) < datetime.now():
                        await self._clear_expired(conn, resource)
                        continue  # Re-read after clear

                    if holder == agent_id:
                        logger.debug(
                            "SovereignLock: Resource %s acquired by %s", resource, agent_id
                        )
                        return True

                # Wait for chance
                await asyncio.sleep(0.1)

        logger.warning("SovereignLock: Timeout acquiring %s for %s", resource, agent_id)
        return False

    async def release(self, resource: str, agent_id: str):
        """Registers a 'release' intent and flattens the result."""
        async with self._engine.session() as conn:
            await conn.execute(
                "INSERT INTO lock_intents (resource, agent_id, action) VALUES (?, ?, ?)",
                (resource, agent_id, "release"),
            )
            await conn.commit()
            await self._reduce_resource(conn, resource)
            logger.debug("SovereignLock: Resource %s released by %s", resource, agent_id)

    async def is_locked(self, resource: str) -> bool:
        """Check current state without waiting."""
        async with self._engine.session() as conn:
            cursor = await conn.execute(
                "SELECT holder_agent, expires_at FROM lock_state WHERE resource = ?", (resource,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
            holder, expiry = row
            if expiry and datetime.fromisoformat(expiry) < datetime.now():
                return False
            return holder is not None

    # ─── Private Reduction Logic ───────────────────────────────────────

    async def _reduce_resource(self, conn: aiosqlite.Connection, resource: str):
        """The 'Reduction' logic: flattens the intent history into current state."""
        # 1. Clear expired intents
        now = datetime.now().isoformat()
        await conn.execute(
            "DELETE FROM lock_intents WHERE expires_at < ? AND action = 'request'", (now,)
        )

        # 2. Get unhandled intents for this resource
        cursor = await conn.execute(
            "SELECT holder_agent FROM lock_state WHERE resource = ?", (resource,)
        )
        state_row = await cursor.fetchone()
        current_holder = state_row[0] if state_row else None

        # Check for release intent for current holder
        if current_holder:
            cursor = await conn.execute(
                "SELECT id FROM lock_intents WHERE resource = ? AND agent_id = ? "
                "AND action = 'release' ORDER BY id DESC LIMIT 1",
                (resource, current_holder),
            )
            if await cursor.fetchone():
                # Holder released. Delete related intents and clear state.
                await conn.execute(
                    "DELETE FROM lock_intents WHERE resource = ? AND agent_id = ?",
                    (resource, current_holder),
                )
                await conn.execute("DELETE FROM lock_state WHERE resource = ?", (resource,))
                current_holder = None

        # Pick the next candidate (FIFO + Priority)
        if not current_holder:
            cursor = await conn.execute(
                "SELECT agent_id, expires_at FROM lock_intents "
                "WHERE resource = ? AND action = 'request' "
                "ORDER BY priority DESC, id ASC LIMIT 1",
                (resource,),
            )
            row = await cursor.fetchone()
            if row:
                new_holder, new_expiry = row
                await conn.execute(
                    "INSERT OR REPLACE INTO lock_state (resource, holder_agent, acquired_at, "
                    "expires_at) VALUES (?, ?, ?, ?)",
                    (resource, new_holder, datetime.now().isoformat(), new_expiry),
                )
                # Cleanup depth info
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM lock_intents WHERE resource = ? AND action = 'request'",
                    (resource,),
                )
                count_row = await cursor.fetchone()
                depth = count_row[0] if count_row else 0
                await conn.execute(
                    "UPDATE lock_state SET queue_depth = ? WHERE resource = ?", (depth, resource)
                )

        await conn.commit()

    async def _clear_expired(self, conn: aiosqlite.Connection, resource: str):
        """Cleanup expired lock state."""
        await conn.execute("DELETE FROM lock_state WHERE resource = ?", (resource,))
        await conn.commit()
        await self._reduce_resource(conn, resource)
