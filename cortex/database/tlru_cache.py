"""
CORTEX v5.3 — Time-aware LRU Cache (TLRU).

Bounded-memory deduplication cache with automatic TTL eviction.
Replaces unbounded dict caches (Nexus dedup, etc.) to prevent
memory leaks under sustained write load.

Derivation: Ω₂ (Entropic Asymmetry) — bounded memory = bounded entropy cost.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Final, final

__all__ = ["TLRUCache"]

_DEFAULT_MAXSIZE: Final[int] = 100_000
_DEFAULT_TTL: Final[float] = 3600.0


@final
class TLRUCache:
    """Time-aware LRU Cache with strict memory bounds.

    Features:
        - O(1) lookup, insert, eviction
        - Automatic TTL expiry on access
        - LRU eviction when capacity is reached
        - Periodic bulk cleanup via cleanup_expired()

    Memory: ~120 bytes per entry × maxsize ≈ 12MB at 100K entries.
    """

    __slots__ = ("_cache", "_maxsize", "_ttl")

    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE, ttl: float = _DEFAULT_TTL) -> None:
        if maxsize < 1:
            raise ValueError(f"maxsize must be >= 1, got {maxsize}")
        if ttl <= 0:
            raise ValueError(f"ttl must be > 0, got {ttl}")
        self._cache: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired. O(1)."""
        if key not in self._cache:
            return False
        timestamp, _ = self._cache[key]
        if time.monotonic() - timestamp > self._ttl:
            del self._cache[key]
            return False
        # Move to end on access (LRU refresh)
        self._cache.move_to_end(key)
        return True

    def __setitem__(self, key: str, value: float) -> None:
        """Insert or update a key. Evicts LRU entry if at capacity. O(1)."""
        now = time.monotonic()
        if key in self._cache:
            # Update existing — move to end
            self._cache[key] = (now, value)
            self._cache.move_to_end(key)
            return
        # Evict oldest if full
        if len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = (now, value)

    def __getitem__(self, key: str) -> float:
        """Get value by key. Raises KeyError if missing or expired."""
        if key not in self._cache:
            raise KeyError(key)
        timestamp, value = self._cache[key]
        if time.monotonic() - timestamp > self._ttl:
            del self._cache[key]
            raise KeyError(key)
        self._cache.move_to_end(key)
        return value

    def get(self, key: str, default: float | None = None) -> float | None:
        """Get value with default. O(1)."""
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self) -> int:
        return len(self._cache)

    def __bool__(self) -> bool:
        return bool(self._cache)

    def clear(self) -> None:
        """Remove all entries."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of evicted items.

        Call periodically (e.g., every 5 min) to reclaim memory proactively.
        """
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._cache.items() if now - ts > self._ttl]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def ttl(self) -> float:
        return self._ttl

    @property
    def hit_ratio_estimate(self) -> float:
        """Rough estimate: fraction of non-expired entries."""
        if not self._cache:
            return 0.0
        now = time.monotonic()
        alive = sum(1 for ts, _ in self._cache.values() if now - ts <= self._ttl)
        return alive / len(self._cache)
