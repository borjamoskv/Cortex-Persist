# [C5-REAL] Exergy-Maximized
"""CORTEX Level 3 Copilot - Suggestion Cache (LRU).

Deduplicates identical context→suggestion mappings.
Prevents redundant LLM calls when the human revisits the same position.

Features:
  - LRU eviction (configurable max size)
  - Per-entry TTL expiration
  - File-based invalidation (on save events)
  - Hit/miss telemetry
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict

from pydantic import BaseModel

from legacy_research.agents.copilot_contracts import SuggestionBatch

logger = logging.getLogger("cortex.agents.copilot.cache")


# ── Models ────────────────────────────────────────────────────────


class CacheStats(BaseModel):
    """Telemetry for cache performance."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    size: int = 0
    max_size: int = 128
    hit_rate: float = 0.0


class _CacheEntry:
    """Internal cache entry with timestamp for TTL."""

    __slots__ = ("batch", "context_hash", "created_at", "file_paths")

    def __init__(
        self,
        batch: SuggestionBatch,
        context_hash: str,
        file_paths: list[str] | None = None,
    ) -> None:
        self.batch = batch
        self.created_at = time.monotonic()
        self.context_hash = context_hash
        self.file_paths = file_paths or []

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if this entry has exceeded its TTL."""
        return (time.monotonic() - self.created_at) > ttl_seconds


# ── Cache ─────────────────────────────────────────────────────────


class SuggestionCache:
    """LRU cache for suggestion deduplication.

    Key: context hash (from _hash_context in copilot_agent.py)
    Value: SuggestionBatch

    Example:
        cache = SuggestionCache(max_size=128, ttl_seconds=60)
        cached = cache.get(context_hash)
        if cached is None:
            batch = await strategy.generate(context)
            cache.put(context_hash, batch, file_paths=[context.cursor.file_path])
    """

    def __init__(
        self,
        *,
        max_size: int = 128,
        ttl_seconds: float = 60.0,
    ) -> None:
        self._max_size = max(1, max_size)
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._stats = CacheStats(max_size=self._max_size)

    def get(self, context_hash: str) -> SuggestionBatch | None:
        """Retrieve a cached suggestion batch by context hash.

        Returns None on miss or expired entry.
        Moves entry to end on hit (LRU refresh).
        """
        entry = self._store.get(context_hash)

        if entry is None:
            self._stats.misses += 1
            self._update_rate()
            return None

        # Check TTL
        if entry.is_expired(self._ttl):
            del self._store[context_hash]
            self._stats.expirations += 1
            self._stats.misses += 1
            self._update_rate()
            logger.debug("Cache expired: %s", context_hash)
            return None

        # LRU refresh: move to end
        self._store.move_to_end(context_hash)
        self._stats.hits += 1
        self._update_rate()
        logger.debug("Cache hit: %s", context_hash)
        return entry.batch

    def put(
        self,
        context_hash: str,
        batch: SuggestionBatch,
        *,
        file_paths: list[str] | None = None,
    ) -> None:
        """Store a suggestion batch in the cache.

        If the cache is full, evicts the least-recently-used entry.

        Args:
            context_hash: Hash of the context that produced this batch.
            batch: The suggestion batch to cache.
            file_paths: File paths associated with this context (for invalidation).
        """
        # If already present, update in place
        if context_hash in self._store:
            self._store.move_to_end(context_hash)
            self._store[context_hash] = _CacheEntry(batch, context_hash, file_paths)
            return

        # Evict if at capacity
        while len(self._store) >= self._max_size:
            evicted_key, _ = self._store.popitem(last=False)
            self._stats.evictions += 1
            logger.debug("Cache evicted: %s", evicted_key)

        self._store[context_hash] = _CacheEntry(batch, context_hash, file_paths)
        self._stats.size = len(self._store)

    def invalidate(self, file_path: str) -> int:
        """Invalidate all cache entries associated with a file path.

        Called on file save events to ensure stale suggestions
        are not served after the file changes.

        Args:
            file_path: Path of the saved/changed file.

        Returns:
            Number of entries invalidated.
        """
        to_remove = [key for key, entry in self._store.items() if file_path in entry.file_paths]

        for key in to_remove:
            del self._store[key]

        count = len(to_remove)
        self._stats.invalidations += count
        self._stats.size = len(self._store)

        if count > 0:
            logger.debug("Invalidated %d entries for %s", count, file_path)

        return count

    def clear(self) -> None:
        """Clear the entire cache."""
        size = len(self._store)
        self._store.clear()
        self._stats.size = 0
        logger.debug("Cache cleared (%d entries)", size)

    def stats(self) -> CacheStats:
        """Return current cache telemetry."""
        self._stats.size = len(self._store)
        return self._stats.model_copy()

    @property
    def size(self) -> int:
        """Current number of entries in cache."""
        return len(self._store)

    # ── Internal ──────────────────────────────────────────────────

    def _update_rate(self) -> None:
        """Recalculate hit rate."""
        total = self._stats.hits + self._stats.misses
        self._stats.hit_rate = self._stats.hits / total if total > 0 else 0.0

    def _gc(self) -> int:
        """Garbage collect expired entries. Returns count removed."""
        expired = [key for key, entry in self._store.items() if entry.is_expired(self._ttl)]
        for key in expired:
            del self._store[key]
            self._stats.expirations += 1
        self._stats.size = len(self._store)
        return len(expired)
