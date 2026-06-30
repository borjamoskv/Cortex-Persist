# [C5-REAL] Exergy-Maximized
"""
Tests for TieredCache L1 + L2 behavior.

Legion-Omega hardened:
- OOM: max value size enforcement (values > 64KiB skipped in L2).
- Intruder: Redis keys are namespaced (no cross-cache collision).
- Entropy: L2 miss / decode failure gracefully falls through to miss.
- Chronos: No REDIS_URL → pure L1 mode, zero network calls.
"""

from __future__ import annotations

import asyncio
import json
import pytest

pytest.importorskip("redis")
import redis.asyncio
from babylon60.database.cache import _MAX_REDIS_VALUE_BYTES, CacheEvent, TieredCache

# ─── L1 Behavior (always active) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_set_and_get_l1(monkeypatch):
    """Basic L1 set/get roundtrip."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_basic", l1_size=10)
    await cache.set("key1", "value1")
    result = await cache.get("key1")
    assert result == "value1"


@pytest.mark.asyncio
async def test_l1_miss_returns_none(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_miss")
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_ttl_expiry(monkeypatch):
    """Entropy: expired entries must return None (not stale data)."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_ttl", ttl_seconds=0.01)
    await cache.set("expiring", "soon")
    await asyncio.sleep(0.02)
    result = await cache.get("expiring")
    assert result is None


@pytest.mark.asyncio
async def test_lru_eviction(monkeypatch):
    """OOM: L1 must evict oldest entries when capacity is exceeded."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[int] = TieredCache("test_lru", l1_size=3)
    for i in range(5):
        await cache.set(f"k{i}", i)
    # k0, k1 should have been evicted
    assert await cache.get("k0") is None
    assert await cache.get("k1") is None
    # k4 must still be present
    assert await cache.get("k4") == 4


@pytest.mark.asyncio
async def test_invalidate_clears_matching_keys(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_invalidate")
    await cache.set("project:alpha:fact:1", "data1")
    await cache.set("project:beta:fact:2", "data2")
    await cache.invalidate("alpha")
    assert await cache.get("project:alpha:fact:1") is None
    assert await cache.get("project:beta:fact:2") == "data2"


@pytest.mark.asyncio
async def test_clear_empties_all(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_clear")
    await cache.set("a", "1")
    await cache.set("b", "2")
    await cache.clear()
    assert await cache.get("a") is None
    assert await cache.get("b") is None


@pytest.mark.asyncio
async def test_subscribe_receives_events(monkeypatch):
    """PubSub: subscriber must receive WARM events on set."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_pubsub")
    q = await cache.subscribe()
    await cache.set("watched", "value")
    event, key = q.get_nowait()
    assert event == CacheEvent.WARM
    assert key == "watched"


# ─── L2 opt-out (Entropy: no Redis URL) ──────────────────────────────


@pytest.mark.asyncio
async def test_no_redis_url_stays_l1_only(monkeypatch):
    """Chronos: without REDIS_URL, _get_redis() must return None without hanging."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_no_redis")
    r = await cache._get_redis()
    assert r is None


@pytest.mark.asyncio
async def test_redis_get_returns_none_when_no_redis(monkeypatch):
    """Entropy: Redis read must return None, not raise, when Redis absent."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_redis_get_none")
    result = await cache._redis_get("any_key")
    assert result is None


# ─── OOM Guard (value size) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_oversized_value_skipped_in_redis(monkeypatch):
    """OOM: values > 64 KiB must not be sent to Redis (silently dropped)."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    cache: TieredCache[str] = TieredCache("test_oom")
    # Generate a value that would exceed the byte limit when JSON-encoded
    oversized = "x" * (_MAX_REDIS_VALUE_BYTES + 1)
    # Should not raise - just silently skip L2 write
    await cache._redis_set("big_key", oversized, 300.0)


# ─── Redis key namespacing (Intruder) ─────────────────────────────────


def test_redis_key_is_namespaced():
    """Intruder: keys must include cache name prefix to prevent collisions."""
    cache = TieredCache("myname")
    key = cache._redis_key("some_key")
    assert key == "cortex:myname:some_key"


def test_redis_keys_differ_across_caches():
    """Two caches with same key must produce different Redis keys."""
    c1 = TieredCache("cache_a")
    c2 = TieredCache("cache_b")
    assert c1._redis_key("k") != c2._redis_key("k")


# ─── Mocked Redis L2 Tests ─────────────────────────────────────────────


class MockRedis:
    def __init__(self):
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.data[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.data:
                del self.data[k]
                count += 1
        return count

    async def scan(
        self, cursor: int, match: str | None = None, count: int | None = None
    ) -> tuple[int, list[str]]:
        # Simple glob-like matching (starts/contains/ends)
        matched_keys = []
        if match:
            clean_match = match.replace("*", "")
            for k in self.data.keys():
                if clean_match in k:
                    matched_keys.append(k)
        else:
            matched_keys = list(self.data.keys())
        return 0, matched_keys


class FaultyMockRedis(MockRedis):
    async def get(self, key: str) -> str | None:
        raise redis.exceptions.RedisError("Redis Connection Error")

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        raise redis.exceptions.RedisError("Redis Write Error")

    async def scan(
        self, cursor: int, match: str | None = None, count: int | None = None
    ) -> tuple[int, list[str]]:
        raise redis.exceptions.RedisError("Redis Scan Error")


@pytest.mark.asyncio
async def test_redis_l2_cache_flow(monkeypatch):
    """Test full tiered cache operations (L1 miss -> L2 hit -> L1 fill)."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    mock_redis = MockRedis()

    monkeypatch.setattr(redis.asyncio, "from_url", lambda *args, **kwargs: mock_redis)

    cache = TieredCache("test_l2", l1_size=2)

    # 1. Set values. They should go to both L1 and L2
    await cache.set("k1", "val1")
    await cache.set("k2", "val2")

    redis_key1 = cache._redis_key("k1")
    redis_key2 = cache._redis_key("k2")
    assert mock_redis.data[redis_key1] == json.dumps("val1")
    assert mock_redis.data[redis_key2] == json.dumps("val2")

    # 2. Evict k1 from L1 (size is 2, insert third key)
    await cache.set("k3", "val3")
    assert "k1" not in cache.l1

    # 3. Read k1, should cause L1 miss, L2 hit, and L1 repopulation
    val = await cache.get("k1")
    assert val == "val1"
    assert "k1" in cache.l1

    # 4. Invalidate pattern
    await cache.invalidate("k2")
    assert await cache.get("k2") is None
    assert mock_redis.data.get(cache._redis_key("k2")) is None

    # 5. Clear cache
    await cache.clear()
    assert len(cache.l1) == 0
    assert len(mock_redis.data) == 0


@pytest.mark.asyncio
async def test_redis_l2_oversized_guard(monkeypatch):
    """Ensure L2 skip logic works with active Redis."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    mock_redis = MockRedis()

    monkeypatch.setattr(redis.asyncio, "from_url", lambda *args, **kwargs: mock_redis)

    cache = TieredCache("test_oversized", l1_size=2)
    oversized = "y" * (_MAX_REDIS_VALUE_BYTES + 1)

    await cache.set("big", oversized)
    # L1 should have it
    assert await cache.get("big") == oversized
    # L2 should NOT have it
    assert mock_redis.data.get(cache._redis_key("big")) is None


@pytest.mark.asyncio
async def test_redis_fault_tolerance(monkeypatch):
    """Ensure exceptions in Redis are caught and handled gracefully."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    faulty_redis = FaultyMockRedis()

    monkeypatch.setattr(redis.asyncio, "from_url", lambda *args, **kwargs: faulty_redis)

    cache = TieredCache("test_fault", l1_size=2)

    # Set should succeed (write to L1 works, L2 fails silently)
    await cache.set("k1", "val1")
    assert await cache.get("k1") == "val1"

    # Force L1 miss to trigger L2 get which raises error
    del cache.l1["k1"]
    assert await cache.get("k1") is None

    # Invalidate should handle error gracefully
    await cache.invalidate("k1")

    # Clear should handle error gracefully
    await cache.clear()
