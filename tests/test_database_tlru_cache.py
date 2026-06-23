# [C5-REAL] Exergy-Maximized
"""Tests for babylon60.database.tlru_cache - Time-aware LRU Cache.

C5-REAL audit remediation: database/ coverage gap.
"""

import time
from unittest.mock import patch

import pytest

from babylon60.database.tlru_cache import TLRUCache


# ── Construction ─────────────────────────────────────────────────────────


class TestConstruction:
    def test_default_params(self):
        c = TLRUCache()
        assert c.maxsize == 100_000
        assert c.ttl == 3600.0

    def test_custom_params(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        assert c.maxsize == 10
        assert c.ttl == 60.0

    def test_invalid_maxsize_raises(self):
        with pytest.raises(ValueError, match="maxsize"):
            TLRUCache(maxsize=0)
        with pytest.raises(ValueError, match="maxsize"):
            TLRUCache(maxsize=-1)

    def test_invalid_ttl_raises(self):
        with pytest.raises(ValueError, match="ttl"):
            TLRUCache(ttl=0)
        with pytest.raises(ValueError, match="ttl"):
            TLRUCache(ttl=-1.0)


# ── Basic Operations ─────────────────────────────────────────────────────


class TestBasicOperations:
    def test_set_and_get(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        c["key1"] = 42.0
        assert c["key1"] == 42.0

    def test_contains(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        c["key1"] = 1.0
        assert "key1" in c
        assert "key2" not in c

    def test_get_with_default(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        assert c.get("missing") is None
        assert c.get("missing", 99.0) == 99.0

    def test_len(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        assert len(c) == 0
        c["a"] = 1.0
        c["b"] = 2.0
        assert len(c) == 2

    def test_bool(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        assert not c
        c["a"] = 1.0
        assert c

    def test_clear(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        c["a"] = 1.0
        c["b"] = 2.0
        c.clear()
        assert len(c) == 0
        assert "a" not in c

    def test_update_existing_key(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        c["key"] = 1.0
        c["key"] = 2.0
        assert c["key"] == 2.0
        assert len(c) == 1

    def test_missing_key_raises(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        with pytest.raises(KeyError):
            _ = c["nonexistent"]


# ── LRU Eviction ─────────────────────────────────────────────────────────


class TestLRUEviction:
    def test_evicts_oldest_when_full(self):
        c = TLRUCache(maxsize=3, ttl=60.0)
        c["a"] = 1.0
        c["b"] = 2.0
        c["c"] = 3.0
        # Full - inserting d should evict a
        c["d"] = 4.0
        assert len(c) == 3
        assert "a" not in c
        assert "d" in c

    def test_access_refreshes_lru_order(self):
        c = TLRUCache(maxsize=3, ttl=60.0)
        c["a"] = 1.0
        c["b"] = 2.0
        c["c"] = 3.0
        # Access a to refresh it
        _ = c["a"]
        # Now b is oldest - inserting d should evict b
        c["d"] = 4.0
        assert "b" not in c
        assert "a" in c

    def test_contains_refreshes_lru(self):
        c = TLRUCache(maxsize=3, ttl=60.0)
        c["a"] = 1.0
        c["b"] = 2.0
        c["c"] = 3.0
        # Touch a via __contains__
        assert "a" in c
        c["d"] = 4.0
        assert "b" not in c
        assert "a" in c


# ── TTL Expiry ───────────────────────────────────────────────────────────


class TestTTLExpiry:
    def test_expired_key_not_in_contains(self):
        c = TLRUCache(maxsize=10, ttl=0.05)
        c["key"] = 1.0
        time.sleep(0.06)
        assert "key" not in c

    def test_expired_key_raises_on_getitem(self):
        c = TLRUCache(maxsize=10, ttl=0.05)
        c["key"] = 1.0
        time.sleep(0.06)
        with pytest.raises(KeyError):
            _ = c["key"]

    def test_expired_key_returns_default_on_get(self):
        c = TLRUCache(maxsize=10, ttl=0.05)
        c["key"] = 1.0
        time.sleep(0.06)
        assert c.get("key", -1.0) == -1.0

    def test_cleanup_expired_removes_old_entries(self):
        c = TLRUCache(maxsize=100, ttl=0.05)
        for i in range(10):
            c[f"k{i}"] = float(i)
        time.sleep(0.06)
        removed = c.cleanup_expired()
        assert removed == 10
        assert len(c) == 0

    def test_cleanup_preserves_fresh_entries(self):
        c = TLRUCache(maxsize=100, ttl=1.0)
        c["fresh"] = 1.0
        removed = c.cleanup_expired()
        assert removed == 0
        assert "fresh" in c


# ── Hit Ratio ────────────────────────────────────────────────────────────


class TestHitRatio:
    def test_hit_ratio_empty(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        assert c.hit_ratio_estimate == 0.0

    def test_hit_ratio_all_alive(self):
        c = TLRUCache(maxsize=10, ttl=60.0)
        c["a"] = 1.0
        c["b"] = 2.0
        assert c.hit_ratio_estimate == 1.0

    def test_hit_ratio_partial_expired(self):
        c = TLRUCache(maxsize=10, ttl=0.05)
        c["old"] = 1.0
        time.sleep(0.06)
        c["new"] = 2.0
        ratio = c.hit_ratio_estimate
        assert 0.0 < ratio < 1.0
