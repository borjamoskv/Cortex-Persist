"""
CORTEX v6.0 — Tiered Caching Strategy.

Multi-level cache with L1 (in-process LRU) and optional L2 (Redis).
L2 activates automatically if REDIS_URL is set in the environment.

Legion-Omega immunity applied:
- OOM: JSON serialization with fallback + max value size enforcement.
- Intruder: Namespaced Redis keys (cortex:<name>:<key>) prevent collisions.
- Entropy: Graceful None/bytes/decode failure handling on L2 reads.
- Chronos: 0.5s timeout on all Redis ops; silently falls through on failure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import OrderedDict
from enum import Enum
from typing import Generic, Optional, TypeVar

__all__ = ["T", "CacheEvent", "TieredCache", "_MAX_REDIS_VALUE_BYTES"]

T = TypeVar("T")

logger = logging.getLogger(__name__)

# Hard limit: values larger than this are never stored in Redis.
# Prevents OOM from oversized payloads being serialized to remote cache.
_MAX_REDIS_VALUE_BYTES: int = 65_536  # 64 KiB

# Timeout for all Redis I/O operations (seconds).
_REDIS_OP_TIMEOUT: float = 0.5


class CacheEvent(Enum):
    INVALIDATE = "invalidate"
    WARM = "warm"
    CLEAR = "clear"


class TieredCache(Generic[T]):
    """Multi-tier cache with pub/sub invalidation.

    Tiers:
    - L1: In-memory LRU (per-process, always active)
    - L2: Redis (optional, activated by REDIS_URL env var)

    Fallback semantics:
    - L2 unavailable / timeout → silent miss, falls through to caller.
    - L2 decode error → silent miss (treats as cache miss, not error).
    """

    def __init__(self, name: str, l1_size: int = 1000, ttl_seconds: float = 300.0):
        self.name = name
        self.l1: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self.l1_size = l1_size
        self.ttl = ttl_seconds
        self._subscribers: list[asyncio.Queue] = []
        self._redis: Optional[object] = None  # aioredis.Redis or None
        self._redis_init_attempted = False

    def _redis_key(self, key: str) -> str:
        """Namespace-prefixed Redis key. Prevents collision across caches/tenants."""
        return f"cortex:{self.name}:{key}"

    async def _get_redis(self) -> Optional[object]:
        """Lazy-init the Redis client if REDIS_URL is set.

        Returns None if Redis is not configured or connection fails.
        Idempotent: only attempts connection once per process lifetime.
        """
        if self._redis_init_attempted:
            return self._redis

        self._redis_init_attempted = True
        redis_url = os.environ.get("REDIS_URL", "")
        if not redis_url:
            return None

        try:
            import redis.asyncio as aioredis  # type: ignore[import-not-found]

            self._redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # raw bytes, we control serialization
                socket_timeout=_REDIS_OP_TIMEOUT,
                socket_connect_timeout=_REDIS_OP_TIMEOUT,
            )
            logger.info("TieredCache[%s]: Redis L2 connected at %s", self.name, redis_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "TieredCache[%s]: Redis L2 unavailable, falling back to L1-only: %s",
                self.name,
                exc,
            )
            self._redis = None

        return self._redis

    async def _redis_get(self, key: str) -> Optional[T]:
        """Fetch a value from Redis L2. Returns None on any failure.

        Entropy/Chronos hardened:
        - Handles None (miss), bytes (hit), and JSON decode failures.
        - Times out after _REDIS_OP_TIMEOUT seconds.
        """
        r = await self._get_redis()
        if r is None:
            return None

        try:
            raw: Optional[bytes] = await asyncio.wait_for(
                r.get(self._redis_key(key)),  # type: ignore[union-attr]
                timeout=_REDIS_OP_TIMEOUT,
            )
            if raw is None:
                return None
            try:
                return json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug("TieredCache[%s]: L2 decode failure for key=%s", self.name, key)
                return None
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            return None

    async def _redis_set(self, key: str, value: T, ttl: float) -> None:
        """Store a value in Redis L2. Silently drops on any failure.

        OOM hardened: skips values exceeding _MAX_REDIS_VALUE_BYTES.
        Intruder hardened: namespaced key prevents collision.
        """
        r = await self._get_redis()
        if r is None:
            return

        try:
            serialized = json.dumps(value).encode("utf-8")
        except (TypeError, ValueError):
            # Non-JSON-serializable types are L1-only.
            return

        if len(serialized) > _MAX_REDIS_VALUE_BYTES:
            logger.debug(
                "TieredCache[%s]: Value too large for L2 (%d bytes > %d), L1-only",
                self.name,
                len(serialized),
                _MAX_REDIS_VALUE_BYTES,
            )
            return

        try:
            await asyncio.wait_for(
                r.setex(self._redis_key(key), int(ttl), serialized),  # type: ignore[union-attr]
                timeout=_REDIS_OP_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            pass  # Chronos / network failure — L1 still has the value.

    async def _redis_delete(self, pattern: str) -> None:
        """Delete keys matching pattern from Redis L2. Silently drops on failure."""
        r = await self._get_redis()
        if r is None:
            return

        try:
            scan_pattern = f"cortex:{self.name}:*{pattern}*"
            async for key in r.scan_iter(match=scan_pattern):  # type: ignore[union-attr]
                await asyncio.wait_for(
                    r.delete(key),  # type: ignore[union-attr]
                    timeout=_REDIS_OP_TIMEOUT,
                )
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            pass

    async def _redis_flush(self) -> None:
        """Flush all keys in this cache's namespace from Redis L2."""
        r = await self._get_redis()
        if r is None:
            return

        try:
            async for key in r.scan_iter(  # type: ignore[union-attr]
                match=f"cortex:{self.name}:*"
            ):
                await asyncio.wait_for(
                    r.delete(key),  # type: ignore[union-attr]
                    timeout=_REDIS_OP_TIMEOUT,
                )
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            pass

    # ─── Public API ───────────────────────────────────────────────

    async def get(self, key: str) -> Optional[T]:
        """Get value from L1 → L2 → miss."""
        # L1 check
        if key in self.l1:
            expiry, value = self.l1[key]
            if time.monotonic() > expiry:
                del self.l1[key]
            else:
                self.l1.move_to_end(key)
                return value

        # L2 check
        value = await self._redis_get(key)
        if value is not None:
            # Promote to L1 with remaining TTL (approximated)
            await self._l1_set(key, value, self.ttl)
            return value

        return None

    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Set value in L1 + L2."""
        effective_ttl = ttl or self.ttl
        await self._l1_set(key, value, effective_ttl)
        await self._redis_set(key, value, effective_ttl)
        await self._notify(CacheEvent.WARM, key)

    async def _l1_set(self, key: str, value: T, ttl: float) -> None:
        expiry = time.monotonic() + ttl
        self.l1[key] = (expiry, value)
        self.l1.move_to_end(key)
        while len(self.l1) > self.l1_size:
            self.l1.popitem(last=False)

    async def invalidate(self, pattern: str) -> None:
        """Invalidate entries matching pattern from L1 and L2."""
        keys_to_remove = [k for k in self.l1 if pattern in k]
        for k in keys_to_remove:
            del self.l1[k]
        await self._redis_delete(pattern)
        await self._notify(CacheEvent.INVALIDATE, pattern)

    async def clear(self) -> None:
        """Clear all entries from L1 and L2."""
        self.l1.clear()
        await self._redis_flush()
        await self._notify(CacheEvent.CLEAR, "all")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to cache events."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _notify(self, event: CacheEvent, key: str) -> None:
        """Notify all subscribers of a cache event."""
        for queue in self._subscribers:
            try:
                queue.put_nowait((event, key))
            except asyncio.QueueFull:
                pass
