"""
Sovereign Synchronization (Axiom Ω₂: Entropic Asymmetry).

In-memory coordination with SQLite durability journal.

In a single-process asyncio system, shared memory IS the coordination
primitive. SQLite serves as the persistence/recovery layer, not the
coordination mechanism.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.lock")


class _LockEntry:
    """In-memory state for a single resource lock."""

    __slots__ = ("holder", "expires_at", "waiters")

    def __init__(self):
        self.holder: str | None = None
        self.expires_at: datetime | None = None
        self.waiters: deque[tuple[int, int, str, float, asyncio.Future]] = deque()


class SovereignLock:
    """
    Sovereign Lock: in-memory coordination, SQLite durability.
    Zero-polling, zero-contention, O(1) acquire/release.
    """

    def __init__(self, engine: Any):
        self._engine = engine
        self._db_path = getattr(engine, "db_path", None) or getattr(engine, "_db_path", None)
        self._locks: dict[str, _LockEntry] = defaultdict(_LockEntry)
        self._seq = 0
        self._mu = asyncio.Lock()
        self._db_mu = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None

    @asynccontextmanager
    async def _conn(self):
        """Dedicated aiosqlite connection for persistence."""
        import aiosqlite

        db_path = str(self._db_path or getattr(self._engine, "_db_path", None))
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            yield conn

    async def acquire(
        self,
        resource: str,
        agent_id: str,
        timeout_s: float = 10.0,
        ttl_s: float = 30.0,
        priority: int = 0,
    ) -> bool:
        """Acquire lock. Returns True if acquired within timeout."""
        loop = asyncio.get_event_loop()
        fut: asyncio.Future[bool] = loop.create_future()

        async with self._mu:
            entry = self._locks[resource]
            now = datetime.now(timezone.utc)

            # Evict expired holder
            if entry.holder and entry.expires_at and entry.expires_at < now:
                entry.holder = None
                entry.expires_at = None

            if entry.holder is None:
                # Acquire immediately
                entry.holder = agent_id
                entry.expires_at = now + timedelta(seconds=ttl_s)
                asyncio.ensure_future(self._persist_acquire(resource, agent_id, entry.expires_at))
                logger.debug(
                    "SovereignLock: %s acquired by %s",
                    resource,
                    agent_id,
                )
                self._ensure_reaper()
                return True

            # Enqueue waiter sorted by priority DESC, FIFO
            self._seq += 1
            entry.waiters.append((-priority, self._seq, agent_id, ttl_s, fut))
            entry.waiters = deque(sorted(entry.waiters, key=lambda x: (x[0], x[1])))

        # Wait outside the lock, but periodically check for expired holders
        deadline = asyncio.get_event_loop().time() + timeout_s
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break

            # Calculate how long to wait: min(remaining, holder TTL)
            async with self._mu:
                entry = self._locks[resource]
                wait_time = remaining
                if entry.expires_at:
                    ttl_remaining = (entry.expires_at - datetime.now(timezone.utc)).total_seconds()
                    if ttl_remaining > 0:
                        # Wake up just after TTL expires
                        wait_time = min(remaining, ttl_remaining + 0.05)

            try:
                result = await asyncio.wait_for(asyncio.shield(fut), timeout=wait_time)
                return result
            except asyncio.TimeoutError:
                if fut.done():
                    return fut.result()
                # Try to evict expired holder
                async with self._mu:
                    entry = self._locks[resource]
                    now = datetime.now(timezone.utc)
                    if entry.holder and entry.expires_at and entry.expires_at < now:
                        # Evict ghost holder
                        entry.holder = None
                        entry.expires_at = None
                        # Promote next (which should be us)
                        self._promote_next_inline(entry, resource)
                        if fut.done():
                            return fut.result()

        # Final timeout — clean up
        async with self._mu:
            entry = self._locks[resource]
            entry.waiters = deque(w for w in entry.waiters if w[4] is not fut)
        if fut.done():
            return fut.result()
        logger.warning(
            "SovereignLock: Timeout acquiring %s for %s",
            resource,
            agent_id,
        )
        return False

    async def release(self, resource: str, agent_id: str):
        """Release lock and promote next waiter."""
        new_holder: str | None = None
        new_expires: datetime | None = None

        async with self._mu:
            entry = self._locks[resource]
            if entry.holder != agent_id:
                logger.warning(
                    "SovereignLock: %s tried to release %s " "but holder is %s",
                    agent_id,
                    resource,
                    entry.holder,
                )
                return

            entry.holder = None
            entry.expires_at = None

            # Promote next valid waiter
            self._promote_next_inline(entry, resource)
            new_holder = entry.holder
            new_expires = entry.expires_at

        # Persist outside the lock (fire-and-forget)
        asyncio.ensure_future(self._persist_release(resource, agent_id, new_holder, new_expires))
        logger.debug("SovereignLock: %s released by %s", resource, agent_id)

    def _promote_next_inline(self, entry: _LockEntry, resource: str):
        """Promote next valid waiter. MUST be called holding self._mu."""
        now = datetime.now(timezone.utc)
        while entry.waiters:
            _, _, w_agent, w_ttl, w_fut = entry.waiters.popleft()
            if w_fut.done():
                continue
            entry.holder = w_agent
            entry.expires_at = now + timedelta(seconds=w_ttl)
            w_fut.set_result(True)
            logger.debug(
                "SovereignLock: %s promoted to %s",
                resource,
                w_agent,
            )
            return

    async def is_locked(self, resource: str) -> bool:
        """In-memory check, O(1)."""
        async with self._mu:
            entry = self._locks[resource]
            if entry.holder is None:
                return False
            now = datetime.now(timezone.utc)
            if entry.expires_at and entry.expires_at < now:
                return False
            return True

    # ─── TTL Reaper ────────────────────────────────────────────────────

    def _ensure_reaper(self):
        """Start the TTL reaper if not already running."""
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.ensure_future(self._ttl_reaper())

    async def _ttl_reaper(self):
        """Sweep expired holders every 100ms, promote waiters."""
        while True:
            await asyncio.sleep(0.1)
            async with self._mu:
                now = datetime.now(timezone.utc)
                any_held = False
                for resource, entry in self._locks.items():
                    if entry.holder is None:
                        continue
                    any_held = True
                    if entry.expires_at and entry.expires_at < now:
                        old = entry.holder
                        entry.holder = None
                        entry.expires_at = None
                        # Promote next waiter
                        promoted = self._promote_waiter(entry, now)
                        asyncio.ensure_future(
                            self._persist_release(
                                resource,
                                old,
                                promoted[0] if promoted else None,
                                promoted[1] if promoted else None,
                            )
                        )
                if not any_held:
                    return  # Stop reaper when idle

    @staticmethod
    def _promote_waiter(entry: _LockEntry, now: datetime) -> tuple[str, datetime] | None:
        """Pop next valid waiter and set as holder. Returns (agent, expires) or None."""
        while entry.waiters:
            _, _, w_agent, w_ttl, w_fut = entry.waiters.popleft()
            if w_fut.done():
                continue
            entry.holder = w_agent
            entry.expires_at = now + timedelta(seconds=w_ttl)
            w_fut.set_result(True)
            return (w_agent, entry.expires_at)
        return None

    # ─── Persistence (fire-and-forget) ─────────────────────────────────

    async def _persist_acquire(self, resource: str, agent_id: str, expires_at: datetime):
        """Persist lock acquisition to SQLite."""
        try:
            async with self._db_mu, self._conn() as conn:
                now = datetime.now(timezone.utc).isoformat()
                await conn.execute(
                    "INSERT INTO lock_intents "
                    "(resource, agent_id, action, priority, "
                    "expires_at) VALUES (?, ?, 'request', 0, ?)",
                    (resource, agent_id, expires_at.isoformat()),
                )
                await conn.execute(
                    "INSERT OR REPLACE INTO lock_state "
                    "(resource, holder_agent, acquired_at, "
                    "expires_at, queue_depth) "
                    "VALUES (?, ?, ?, ?, 0)",
                    (resource, agent_id, now, expires_at.isoformat()),
                )
                await conn.commit()
        except Exception:
            logger.exception("Failed to persist acquire")

    async def _persist_release(
        self,
        resource: str,
        agent_id: str,
        new_holder: str | None,
        new_expires: datetime | None,
    ):
        """Persist release + new holder state to SQLite."""
        try:
            async with self._db_mu, self._conn() as conn:
                # Record release intent
                await conn.execute(
                    "INSERT INTO lock_intents "
                    "(resource, agent_id, action) "
                    "VALUES (?, ?, 'release')",
                    (resource, agent_id),
                )
                # Clean old intents
                await conn.execute(
                    "DELETE FROM lock_intents " "WHERE resource = ? AND agent_id = ?",
                    (resource, agent_id),
                )
                if new_holder and new_expires:
                    now = datetime.now(timezone.utc).isoformat()
                    await conn.execute(
                        "INSERT OR REPLACE INTO lock_state "
                        "(resource, holder_agent, acquired_at, "
                        "expires_at, queue_depth) "
                        "VALUES (?, ?, ?, ?, 0)",
                        (
                            resource,
                            new_holder,
                            now,
                            new_expires.isoformat(),
                        ),
                    )
                else:
                    await conn.execute(
                        "DELETE FROM lock_state " "WHERE resource = ?",
                        (resource,),
                    )
                await conn.commit()
        except Exception:
            logger.exception("Failed to persist release")
