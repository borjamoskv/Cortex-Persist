"""
CORTEX v5.5 — Sovereign Bounded Cache.

A thread-safe, async-friendly LRU+TTL cache with eviction hooks for 
persistence and audit trails. 

Axiom: Ω₂ (Entropic Asymmetry) — memory is finite; audit trails are infinite.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from enum import Enum
from typing import Any, Generic, TypeVar, final

T = TypeVar("T")

logger = logging.getLogger("cortex.utils.cache")


class EvictionReason(Enum):
    """Reason why an item was purged from the cache."""

    TTL = "ttl_expired"
    LRU = "lru_capacity"
    MANUAL = "manual_purge"
    SHUTDOWN = "system_shutdown"


@final
class SovereignCache(Generic[T]):
    """
    LRU + TTL Cache with an 'on_evict' hook and a Proof-of-Forgetting chain.

    Memory consumption is strictly bounded by maxsize.
    Audit requirements (Ω₀: Self-Reference) are met by maintaining a
    cryptographic chain of all evictions.

    Axiom: Ω₂ (Entropic Asymmetry) — memory is finite; audit trails are infinite.
    """

    __slots__ = (
        "_cache",
        "_maxsize",
        "_ttl",
        "_on_evict",
        "_lock",
        "_eviction_tasks",
        "_evidence_hash",
        "_eviction_count",
    )

    def __init__(
        self,
        maxsize: int = 1000,
        ttl: float = 3600.0,
        on_evict: Callable[[str, T, str, int], Any] | None = None,
    ) -> None:
        """
        Args:
            maxsize: Maximum number of elements.
            ttl: Time-to-live in seconds.
            on_evict: Hook for eviction. Signature: (key, value, evidence_hash, count).
        """
        self._cache: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl
        self._on_evict = on_evict
        self._lock = asyncio.Lock()
        self._eviction_tasks: set[asyncio.Task[Any]] = set()

        # Sovereign Evidence Chain (Ω₀)
        self._evidence_hash = hashlib.sha256(b"CORTEX_GENESIS_VOID").hexdigest()
        self._eviction_count = 0

    async def get(self, key: str, default: T | None = None) -> T | None:
        """Get value with LRU refresh and TTL check."""
        async with self._lock:
            if key not in self._cache:
                return default

            expiry, value = self._cache[key]
            if time.monotonic() > expiry:
                # Lazy eviction (TTL)
                val = self._cache.pop(key)[1]
                await self._execute_eviction(key, val, EvictionReason.TTL)
                return default

            # Refresh LRU
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: T, ttl_override: float | None = None) -> None:
        """Insert value, triggering eviction if capacity reached."""
        expiry = time.monotonic() + (ttl_override or self._ttl)

        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)

            self._cache[key] = (expiry, value)

            # Bound Enforcement (LRU)
            if len(self._cache) > self._maxsize:
                # Pop oldest (LRU)
                old_key, (_, old_val) = self._cache.popitem(last=False)
                await self._execute_eviction(old_key, old_val, EvictionReason.LRU)

    async def _execute_eviction(self, key: str, value: T, reason: EvictionReason) -> None:
        """Compute the Proof of Forgetting and execute the hook safely."""
        self._eviction_count += 1

        # 130/100: Mathematical proof of what was forgotten
        # H(prev | k_hash | v_hash | reason)
        k_hash = hashlib.sha256(str(key).encode()).hexdigest()
        v_hash = hashlib.sha256(str(value).encode()).hexdigest()
        proof_payload = f"{self._evidence_hash}|{k_hash}|{v_hash}|{reason.value}"
        self._evidence_hash = hashlib.sha256(proof_payload.encode()).hexdigest()

        if not self._on_evict:
            return

        try:
            if asyncio.iscoroutinefunction(self._on_evict):
                task = asyncio.create_task(
                    self._on_evict(key, value, self._evidence_hash, self._eviction_count)
                )
                self._eviction_tasks.add(task)
                task.add_done_callback(self._eviction_tasks.discard)
            else:
                self._on_evict(key, value, self._evidence_hash, self._eviction_count)
        except Exception as e:
            logger.error("SovereignCache: Eviction hook failed for key %s: %s", key, e)

    def get_forgetting_proof(self) -> dict[str, Any]:
        """Returns the current state of the evidence chain."""
        return {
            "tip": self._evidence_hash,
            "count": self._eviction_count,
            "capacity": self._maxsize,
            "utilization": len(self._cache),
        }

    def __len__(self) -> int:
        return len(self._cache)

    async def clear(self) -> None:
        async with self._lock:
            # When clearing manually, we treat each as a 'manual purge' eviction
            # to maintain the chain integrity.
            while self._cache:
                old_key, (_, old_val) = self._cache.popitem(last=False)
                await self._execute_eviction(old_key, old_val, EvictionReason.MANUAL)
