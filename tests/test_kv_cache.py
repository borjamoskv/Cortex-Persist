# Tests — KV Prefix Cache (AX-042)

from cortex.autodidact.kv_cache import KVPrefixCache


def test_hit_miss_basic():
    cache = KVPrefixCache(max_size=10)
    key = cache.compute_prefix("capital", "mev_staged", {"a": 1})
    assert not cache.hit(key)
    cache.store(key, "hash_abc")
    assert cache.hit(key)
    assert cache.get(key) == "hash_abc"


def test_identical_payload_same_key():
    cache = KVPrefixCache()
    k1 = cache.compute_prefix("capital", "mev_staged", {"x": 42, "y": "z"})
    k2 = cache.compute_prefix("capital", "mev_staged", {"x": 42, "y": "z"})
    assert k1 == k2


def test_different_payload_different_key():
    cache = KVPrefixCache()
    k1 = cache.compute_prefix("capital", "mev_staged", {"x": 42})
    k2 = cache.compute_prefix("capital", "mev_staged", {"x": 99})
    assert k1 != k2


def test_different_type_different_key():
    cache = KVPrefixCache()
    k1 = cache.compute_prefix("capital", "action", {"d": 1})
    k2 = cache.compute_prefix("knowledge", "action", {"d": 1})
    assert k1 != k2


def test_lru_eviction():
    cache = KVPrefixCache(max_size=2)
    cache.store("k1", "h1")
    cache.store("k2", "h2")
    cache.store("k3", "h3")  # Evicts k1
    assert not cache.hit("k1")
    assert cache.hit("k2")
    assert cache.hit("k3")
    stats = cache.stats()
    assert stats["evictions"] == 1
    assert stats["size"] == 2


def test_stats_accuracy():
    cache = KVPrefixCache(max_size=10)
    cache.store("a", "1")
    cache.hit("a")  # hit
    cache.hit("b")  # miss
    cache.hit("c")  # miss
    s = cache.stats()
    assert s["hits"] == 1
    assert s["misses"] == 2
    assert s["hit_rate"] == 1 / 3


def test_invalidate():
    cache = KVPrefixCache()
    cache.store("x", "val")
    assert cache.invalidate("x")
    assert not cache.hit("x")
    assert not cache.invalidate("nonexistent")


def test_clear():
    cache = KVPrefixCache()
    cache.store("a", "1")
    cache.store("b", "2")
    cache.clear()
    assert cache.stats()["size"] == 0
