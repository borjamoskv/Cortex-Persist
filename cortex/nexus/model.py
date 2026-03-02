"""
The World Model (Production)
"""

import asyncio
import logging
import os
import time
from typing import Any, Final

from cortex.nexus.db import NexusDB
from cortex.nexus.types import DomainOrigin, IntentType, WorldMutation

logger = logging.getLogger("cortex.nexus.model")

_DEFAULT_DB: Final[str] = os.path.expanduser("~/.cortex/nexus.db")
_DEDUP_TTL: Final[float] = 3600.0  # 1 hour dedup window
_MAX_HOOK_CONCURRENCY: Final[int] = 8


class NexusWorldModel:
    """The single source of truth. All domains mutate this; none talk directly.

    Production-grade with:
        - SQLite WAL backend for multi-process safety
        - Priority-based processing
        - SHA-256 idempotency dedup
        - Parallel async hooks
        - Direct query interface
    """

    __slots__ = ("_db", "_hooks", "_stats", "_dedup_cache")

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db = NexusDB(db_path)
        self._hooks: dict[IntentType, list[Any]] = {}
        self._dedup_cache: dict[str, float] = {}  # key → timestamp (in-memory fast path)
        self._stats: dict[str, int] = {
            "total_mutations": 0,
            "deduplicated": 0,
            "hook_fires": 0,
            "hook_errors": 0,
        }

    # ─── Core Mutation Interface ─────────────────────────────────────

    async def mutate(self, mutation: WorldMutation) -> bool:
        """The ONLY entry point for changing the World Model.

        Returns True if mutation was applied, False if deduplicated.
        """
        # Fast-path dedup (in-memory)
        key = mutation.idempotency_key
        now = time.time()

        if key in self._dedup_cache:
            if now - self._dedup_cache[key] < _DEDUP_TTL:
                self._stats["deduplicated"] += 1
                logger.debug("NEXUS DEDUP: %s (key=%s)", mutation.intent.name, key)
                return False

        # Persist to SQLite (cross-process visible)
        inserted = await asyncio.get_event_loop().run_in_executor(None, self._db.insert, mutation)

        if not inserted:
            self._stats["deduplicated"] += 1
            self._dedup_cache[key] = now
            return False

        self._dedup_cache[key] = now
        self._stats["total_mutations"] += 1

        logger.info(
            "🌀 NEXUS [%s → %s] P%d project=%s conf=%.2f key=%s",
            mutation.origin.name,
            mutation.intent.name,
            mutation.priority.value,
            mutation.project,
            mutation.confidence,
            key,
        )

        # Fire hooks in parallel
        await self._dispatch_hooks(mutation)
        return True

    # ─── Reactive Hooks (Parallel Dispatch) ───────────────────────────

    def on(self, intent: IntentType, callback: Any) -> None:
        """Register a reactive hook."""
        self._hooks.setdefault(intent, []).append(callback)

    async def _dispatch_hooks(self, mutation: WorldMutation) -> None:
        """Fire all hooks for this intent in PARALLEL."""
        hooks = self._hooks.get(mutation.intent, [])
        if not hooks:
            return

        async def _safe_fire(hook):
            try:
                result = hook(mutation)
                if asyncio.iscoroutine(result):
                    await result
                self._stats["hook_fires"] += 1
            except (TypeError, ValueError, RuntimeError, OSError) as exc:
                self._stats["hook_errors"] += 1
                logger.error("Hook %s failed: %s", hook.__name__, exc)

        # Parallel execution with concurrency limit
        sem = asyncio.Semaphore(_MAX_HOOK_CONCURRENCY)

        async def _throttled(hook):
            async with sem:
                await _safe_fire(hook)

        await asyncio.gather(*[_throttled(h) for h in hooks])

    # ─── Query Interface ──────────────────────────────────────────────

    async def query(
        self,
        origin: DomainOrigin | None = None,
        intent: IntentType | None = None,
        project: str | None = None,
        since: float | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Ask the World Model: 'What happened?'

        Examples:
            nexus.query(origin=DomainOrigin.MOLTBOOK, since=time.time()-3600)
            nexus.query(intent=IntentType.SHADOWBAN_DETECTED)
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._db.query, origin, intent, project, since, limit
        )

    # ─── Lifecycle ─────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Clean up in-memory caches."""
        self._dedup_cache.clear()
        logger.info("🛑 NEXUS shutdown. Stats: %s", self._stats)

    @property
    def stats(self) -> dict[str, int]:
        return self._stats.copy()

    @property
    def mutation_count(self) -> int:
        return self._db.count()
