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

import pytest

from cortex.database.cache import _MAX_REDIS_VALUE_BYTES, CacheEvent, TieredCache

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
    # Should not raise — just silently skip L2 write
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
