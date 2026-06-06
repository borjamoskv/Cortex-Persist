# [C5-REAL] Exergy-Maximized
"""
Sovereign Synchronization (Axiom Ω₂: Entropic Asymmetry).

Implementation of a Lock-Free synchronization mechanism.
Instead of blocking threads/coroutines, agents append their INTENT to a shared ledger.
A projection (lock_state) determines the current truth.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.lock")

_REDUCE_LOCKS: dict[tuple[str, int], asyncio.Lock] = {}


def _get_local_lock(db_path: str | None) -> asyncio.Lock:
    key = db_path or ":memory:"
    loop_id = id(asyncio.get_running_loop())
    lock_key = (key, loop_id)
    if lock_key not in _REDUCE_LOCKS:
        _REDUCE_LOCKS[lock_key] = asyncio.Lock()
    return _REDUCE_LOCKS[lock_key]


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
        # Queue expiration: the intent should only live as long as we are willing to wait.
        # We add a small buffer (5.0s) so it doesn't vanish while we're processing.
        queue_expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=timeout_s + 5.0)
        ).isoformat()

        # We encode the requested TTL in the action field to preserve schema compatibility.
        action_val = f"request:{ttl_s}"

        # 1. Append Intent (Atomic operation in SQLite)
        async with self._engine.session() as conn:
            await conn.execute(
                "INSERT INTO lock_intents (resource, agent_id, action, priority, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (resource, agent_id, action_val, priority, queue_expires_at),
            )
            await conn.commit()

            # 2. Trigger immediate localized reduction
            await self._reduce_resource(conn, resource)

            # 3. Wait for state collapse (polling projection)
            start_time = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_s:
                async with conn.execute(
                    "SELECT holder_agent, expires_at FROM lock_state WHERE resource = ?",
                    (resource,),
                ) as cursor:
                    row = await cursor.fetchone()
                if row:
                    holder, expiry = row
                    # Clean up if expired
                    if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
                        await self._clear_expired(conn, resource)
                        continue  # Re-read after clear

                    if holder == agent_id:
                        logger.debug(
                            "SovereignLock: Resource %s acquired by %s", resource, agent_id
                        )
                        return True

                # Wait for chance
                await asyncio.sleep(0.1)

            # Timeout path - must clean up intent to prevent zombie locks
            # One last check to avoid race condition where we just got the lock
            async with conn.execute(
                "SELECT holder_agent FROM lock_state WHERE resource = ?", (resource,)
            ) as cursor:
                row = await cursor.fetchone()
            if row and row[0] == agent_id:
                logger.debug(
                    "SovereignLock: Resource %s acquired by %s right at timeout",
                    resource,
                    agent_id,
                )
                return True

            # We didn't get it. Remove our request intent.
            await conn.execute(
                "DELETE FROM lock_intents WHERE resource = ? AND agent_id = ? AND action LIKE 'request%'",
                (resource, agent_id),
            )
            await self._reduce_resource_inner(conn, resource)

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
            async with conn.execute(
                "SELECT holder_agent, expires_at FROM lock_state WHERE resource = ?", (resource,)
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                return False
            holder, expiry = row
            if expiry and datetime.fromisoformat(expiry) < datetime.now(timezone.utc):
                return False
            return holder is not None

    # ─── Private Reduction Logic ───────────────────────────────────────

    async def _reduce_resource(self, conn: aiosqlite.Connection, resource: str):
        await self._reduce_resource_inner(conn, resource)

    async def _reduce_resource_inner(self, conn: aiosqlite.Connection, resource: str):
        """The 'Reduction' logic: flattens the intent history into current state."""
        # 1. Clear expired intents
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "DELETE FROM lock_intents WHERE expires_at < ? AND action LIKE 'request%'", (now,)
        )

        # 2. Get unhandled intents for this resource
        async with conn.execute(
            "SELECT holder_agent FROM lock_state WHERE resource = ?", (resource,)
        ) as cursor:
            state_row = await cursor.fetchone()
        current_holder = state_row[0] if state_row else None

        # Check for release intent for current holder
        if current_holder:
            async with conn.execute(
                "SELECT id FROM lock_intents WHERE resource = ? AND agent_id = ? "
                "AND action = 'release' ORDER BY id DESC LIMIT 1",
                (resource, current_holder),
            ) as cursor:
                has_release = await cursor.fetchone() is not None
            if has_release:
                # Holder released. Delete related intents and clear state.
                await conn.execute(
                    "DELETE FROM lock_intents WHERE resource = ? AND agent_id = ?",
                    (resource, current_holder),
                )
                await conn.execute("DELETE FROM lock_state WHERE resource = ?", (resource,))
                current_holder = None

        # Pick the next candidate (FIFO + Priority)
        if not current_holder:
            async with conn.execute(
                "SELECT agent_id, action FROM lock_intents "
                "WHERE resource = ? AND action LIKE 'request%' "
                "ORDER BY priority DESC, id ASC LIMIT 1",
                (resource,),
            ) as cursor:
                row = await cursor.fetchone()
            if row:
                new_holder, action_val = row

                # Decode TTL from action (e.g., 'request:30.0')
                ttl_s = 30.0
                if ":" in action_val:
                    try:
                        ttl_s = float(action_val.split(":")[1])
                    except ValueError:

                        pass

                new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()

                await conn.execute(
                    "INSERT OR REPLACE INTO lock_state (resource, holder_agent, acquired_at, "
                    "expires_at) VALUES (?, ?, ?, ?)",
                    (
                        resource,
                        new_holder,
                        datetime.now(timezone.utc).isoformat(),
                        new_expiry,
                    ),
                )
                # Cleanup depth info
                async with conn.execute(
                    "SELECT COUNT(*) FROM lock_intents WHERE resource = ? AND action LIKE 'request%'",
                    (resource,),
                ) as cursor:
                    count_row = await cursor.fetchone()
                depth = count_row[0] if count_row else 0
                await conn.execute(
                    "UPDATE lock_state SET queue_depth = ? WHERE resource = ?", (depth, resource)
                )

        await conn.commit()

    async def _clear_expired(self, conn: aiosqlite.Connection, resource: str):
        """Cleanup expired lock state."""
        # Get the current expired holder so we can remove their intents
        async with conn.execute(
            "SELECT holder_agent FROM lock_state WHERE resource = ?", (resource,)
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0]:
            expired_holder = row[0]
            # Remove their request intent so they don't immediately reclaim it
            await conn.execute(
                "DELETE FROM lock_intents WHERE resource = ? AND agent_id = ?",
                (resource, expired_holder),
            )

        await conn.execute("DELETE FROM lock_state WHERE resource = ?", (resource,))
        await self._reduce_resource_inner(conn, resource)
