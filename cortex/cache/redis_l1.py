# [C5-REAL] Exergy-Maximized
"""
Redis L1 Cache - Distributed Working Memory for LEGION-10k.

Provides a thread-safe, namespace-prefixed cache layer with
graceful degradation when Redis is unavailable.

Reality Level: C5-REAL
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Any

try:
    import redis
    from redis.exceptions import RedisError

    HAS_REDIS = True
except ImportError:
    redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[assignment,misc]
    HAS_REDIS = False

logger = logging.getLogger("cortex.cache.redis_l1")

_PREFIX = "cortex:l1:"


class RedisL1Cache:
    """Redis-backed L1 cache with graceful fallback.

    When Redis is unavailable (not installed or server down),
    all operations return safe defaults without raising.
    """

    _instance: RedisL1Cache | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        default_ttl: int = 300,
        *,
        _client: Any = None,
    ) -> None:
        self._host = host
        self._port = port
        self._db = db
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._client: Any = _client

        if self._client is None and HAS_REDIS:
            # Skip Redis connection in standard test suites unless explicitly enabled
            if os.environ.get("CORTEX_TESTING") == "1" and os.environ.get("CORTEX_TEST_REDIS") != "1":
                self._client = None
            else:
                try:
                    connect_timeout = 0.1 if os.environ.get("CORTEX_TESTING") == "1" else 2.0
                    socket_timeout = 0.1 if os.environ.get("CORTEX_TESTING") == "1" else 1.0
                    client = redis.Redis(  # pyright: ignore[reportOptionalMemberAccess]
                        host=host,
                        port=port,
                        db=db,
                        socket_connect_timeout=connect_timeout,
                        socket_timeout=socket_timeout,
                        decode_responses=False,
                    )
                    # Eagerly ping to check availability and avoid downstream connection delays
                    client.ping()
                    self._client = client
                    logger.info("Redis L1 cache instance created: %s:%d/%d", host, port, db)
                except (OSError, ConnectionError, TimeoutError, RedisError, Exception) as exc:
                    logger.warning("Redis L1 unavailable (%s), operating in pass-through mode", exc)
                    self._client = None

    @classmethod
    def singleton(cls, **kwargs: Any) -> RedisL1Cache:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance

    @property
    def available(self) -> bool:
        return self._client is not None

    def _key(self, key: str) -> str:
        return f"{_PREFIX}{key}"

    # ── Core Operations ─────────────────────────────────────

    def get(self, key: str) -> bytes | None:
        """L1 cache lookup."""
        if not self._client:
            self._misses += 1
            return None
        try:
            val = self._client.get(self._key(key))
            if val is not None:
                self._hits += 1
            else:
                self._misses += 1
            return val
        except (OSError, ConnectionError, TimeoutError, RedisError) as exc:
            logger.warning("Redis L1 error on get (%s), disabling cache fallback", exc)
            self._client = None
            self._misses += 1
            return None

    def set(self, key: str, value: bytes, ttl: int | None = None) -> bool:
        """Cache a value with TTL (seconds)."""
        if not self._client:
            return False
        try:
            return bool(self._client.setex(self._key(key), ttl or self._default_ttl, value))
        except (OSError, ConnectionError, TimeoutError, RedisError) as exc:
            logger.warning("Redis L1 error on set (%s), disabling cache fallback", exc)
            self._client = None
            return False

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], bytes],
        ttl: int | None = None,
    ) -> bytes:
        """Cache-aside pattern: return cached value or compute and cache."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute_fn()
        self.set(key, value, ttl)
        return value

    def invalidate(self, key: str) -> bool:
        """Delete a cached key."""
        if not self._client:
            return False
        try:
            return bool(self._client.delete(self._key(key)))
        except (OSError, ConnectionError, TimeoutError, RedisError) as exc:
            logger.warning("Redis L1 error on invalidate (%s), disabling cache fallback", exc)
            self._client = None
            return False

    def flush_namespace(self, prefix: str) -> int:
        """Delete all keys matching cortex:l1:{prefix}*."""
        if not self._client:
            return 0
        try:
            pattern = f"{_PREFIX}{prefix}*"
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except (OSError, ConnectionError, TimeoutError, RedisError) as exc:
            logger.warning("Redis L1 error on flush_namespace (%s), disabling cache fallback", exc)
            self._client = None
            return 0

    def health_check(self) -> dict[str, Any]:
        """Redis connectivity and latency check."""
        result: dict[str, Any] = {
            "available": False,
            "has_redis_lib": HAS_REDIS,
            "host": self._host,
            "port": self._port,
            "latency_ms": -1.0,
        }
        if not self._client:
            return result
        try:
            t0 = time.perf_counter()
            self._client.ping()
            latency = (time.perf_counter() - t0) * 1000
            result["available"] = True
            result["latency_ms"] = round(latency, 3)
            info = self._client.info("memory")
            result["used_memory_bytes"] = info.get("used_memory", 0)
            result["used_memory_human"] = info.get("used_memory_human", "N/A")
        except (OSError, ConnectionError, TimeoutError, RedisError) as exc:
            result["error"] = str(exc)
        return result

    def stats(self) -> dict[str, Any]:
        """Hit/miss ratio and cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / total, 4) if total > 0 else 0.0,
            "total_requests": total,
            "available": self.available,
        }

    def cache_key_hash(self, *parts: str) -> str:
        """Generate a deterministic cache key from parts."""
        raw = ":".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
