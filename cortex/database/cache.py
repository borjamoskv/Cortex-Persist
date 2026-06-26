# [C5-REAL] Exergy-Maximized
"""
Tiered Caching Strategy.

Multi-level cache with L1 (Memory) and PubSub invalidation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from enum import Enum
from typing import Generic, TypeVar

__all__ = ["CacheEvent", "T", "TieredCache"]

_MAX_REDIS_VALUE_BYTES = 64 * 1024  # 64 KiB threshold for L2 storage

T = TypeVar("T")

logger = logging.getLogger(__name__)


class CacheEvent(Enum):
    INVALIDATE = "invalidate"
    WARM = "warm"
    CLEAR = "clear"


class TieredCache(Generic[T]):
    """
    Multi-tier cache with pub/sub invalidation.

    Tiers:
    - L1: In-memory LRU (per-process)
    - L2/L3: Redis or Persistent Store
    """

    def __init__(self, name: str, l1_size: int = 1000, ttl_seconds: float = 300.0):
        self.name = name
        self.l1: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self.l1_size = l1_size
        self.ttl = ttl_seconds
        self._subscribers: list[asyncio.Queue] = []
        self._redis_client = None

    def _redis_key(self, key: str) -> str:
        """Namespace key for Redis storage."""
        return f"cortex:{self.name}:{key}"

    async def get(self, key: str) -> T | None:
        """Get value from cache."""
        # L1 check
        if key in self.l1:
            expiry, value = self.l1[key]
            if time.monotonic() > expiry:
                del self.l1[key]
                # L1 expired, fall through to L2 check
            else:
                # Move to end (LRU)
                self.l1.move_to_end(key)
                return value

        # L2 check
        val = await self._redis_get(key)
        if val is not None:
            # Populate L1
            expiry = time.monotonic() + self.ttl
            self.l1[key] = (expiry, val)
            self.l1.move_to_end(key)
            while len(self.l1) > self.l1_size:
                self.l1.popitem(last=False)
        return val

    async def _get_redis(self):
        """Internal helper to resolve Redis client if REDIS_URL is configured."""
        if self._redis_client is not None:
            return self._redis_client

        import os

        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            return None

        try:
            import redis.asyncio as aioredis

            self._redis_client = aioredis.from_url(redis_url, decode_responses=True)
            return self._redis_client
        except (ImportError, OSError, ValueError):
            logger.exception("Failed to initialize Redis client for cache %s", self.name)
            return None

    async def _redis_get(self, key: str) -> T | None:
        """Internal helper for Redis get."""
        client = await self._get_redis()
        if client is None:
            return None
        redis_key = self._redis_key(key)
        try:
            raw_val = await client.get(redis_key)
            if raw_val is None:
                return None
            import json

            return json.loads(raw_val)
        except (ValueError, TypeError, RuntimeError, OSError) as e:
            logger.warning("Redis get failed for key %s: %s", key, e)
            return None

    async def _redis_set(self, key: str, value: T, ttl: float):
        """Internal helper for Redis set."""
        client = await self._get_redis()
        if client is None:
            return
        redis_key = self._redis_key(key)
        try:
            import json

            serialized = json.dumps(value)
            # OOM size guard: skip L2 if size > 64KiB
            if len(serialized.encode("utf-8")) > _MAX_REDIS_VALUE_BYTES:
                logger.debug(
                    "Value for key %s exceeds %d bytes, skipping Redis", key, _MAX_REDIS_VALUE_BYTES
                )
                return
            await client.set(redis_key, serialized, ex=int(ttl))
        except (ValueError, TypeError, RuntimeError, OSError) as e:
            logger.warning("Redis set failed for key %s: %s", key, e)

    async def set(self, key: str, value: T, ttl: float | None = None):
        """Set value in cache."""
        duration = ttl or self.ttl
        expiry = time.monotonic() + duration

        # L1 insert
        self.l1[key] = (expiry, value)
        self.l1.move_to_end(key)

        # Evict oldest if over capacity
        while len(self.l1) > self.l1_size:
            self.l1.popitem(last=False)

        # L2 insert
        await self._redis_set(key, value, duration)

        # Notify subscribers
        await self._notify(CacheEvent.WARM, key)

    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        # Remove from L1
        keys_to_remove = [k for k in self.l1.keys() if pattern in k]
        for k in keys_to_remove:
            del self.l1[k]

        # Remove from L2
        client = await self._get_redis()
        if client is not None:
            try:
                redis_pattern = self._redis_key(f"*{pattern}*")
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor, match=redis_pattern, count=100)
                    if keys:
                        await client.delete(*keys)
                    if cursor == 0:
                        break
            except (ValueError, TypeError, RuntimeError, OSError) as e:
                logger.warning("Redis invalidate failed for pattern %s: %s", pattern, e)

        await self._notify(CacheEvent.INVALIDATE, pattern)

    async def clear(self):
        """Clear all cache entries."""
        self.l1.clear()

        # Clear from L2
        client = await self._get_redis()
        if client is not None:
            try:
                redis_pattern = self._redis_key("*")
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor, match=redis_pattern, count=100)
                    if keys:
                        await client.delete(*keys)
                    if cursor == 0:
                        break
            except (ValueError, TypeError, RuntimeError, OSError) as e:
                logger.warning("Redis clear failed: %s", e)

        await self._notify(CacheEvent.CLEAR, "all")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to cache events."""
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    async def _notify(self, event: CacheEvent, key: str):
        """Notify all subscribers."""
        for queue in self._subscribers:
            try:
                queue.put_nowait((event, key))
            except asyncio.QueueFull:
                logger.warning("Cache subscriber queue full, dropping event")
