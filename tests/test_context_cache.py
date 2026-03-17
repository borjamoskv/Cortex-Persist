"""Tests for Context Cache Adapter — Phase 5."""

import time

from cortex.engine.context_cache import ContextCacheManager, EvictionPolicy


class TestContextCacheManager:
    """Context Cache lifecycle tests."""

    def test_create_and_get(self):
        mgr = ContextCacheManager(max_entries=10)
        entry = mgr.create(
            project="test",
            provider="gemini",
            model="gemini-2.0-flash",
            token_count=8192,
            provider_handle="cached_content/abc123",
        )
        assert entry.cache_id
        assert entry.token_count == 8192

        retrieved = mgr.get(entry.cache_id)
        assert retrieved is not None
        assert retrieved.cache_id == entry.cache_id

    def test_get_nonexistent(self):
        mgr = ContextCacheManager()
        assert mgr.get("nonexistent") is None

    def test_invalidate(self):
        mgr = ContextCacheManager()
        entry = mgr.create(
            project="test",
            provider="gemini",
            model="m",
            token_count=100,
        )
        assert mgr.invalidate(entry.cache_id)
        assert mgr.get(entry.cache_id) is None

    def test_invalidate_project(self):
        mgr = ContextCacheManager()
        mgr.create(project="proj_a", provider="gemini", model="m", token_count=100)
        mgr.create(project="proj_a", provider="openai", model="m", token_count=200)
        mgr.create(project="proj_b", provider="gemini", model="m", token_count=300)

        removed = mgr.invalidate_project("proj_a")
        assert removed == 2
        stats = mgr.stats()
        assert stats.total_entries == 1

    def test_get_by_project(self):
        mgr = ContextCacheManager()
        mgr.create(project="alpha", provider="gemini", model="m", token_count=100)
        mgr.create(project="beta", provider="gemini", model="m", token_count=200)

        alpha = mgr.get_by_project("alpha")
        assert len(alpha) == 1
        assert alpha[0].project == "alpha"

    def test_get_by_agent(self):
        mgr = ContextCacheManager()
        mgr.create(
            project="test", provider="gemini", model="m", token_count=100, agent_id="agent_1"
        )
        mgr.create(
            project="test", provider="gemini", model="m", token_count=200, agent_id="agent_2"
        )

        a1 = mgr.get_by_agent("agent_1")
        assert len(a1) == 1
        assert a1[0].agent_id == "agent_1"

    def test_ttl_expiry(self):
        mgr = ContextCacheManager()
        entry = mgr.create(
            project="test",
            provider="gemini",
            model="m",
            token_count=100,
            ttl_seconds=-1,
        )
        # TTL=-1 means already expired
        assert mgr.get(entry.cache_id) is None

    def test_lru_eviction(self):
        mgr = ContextCacheManager(
            max_entries=2,
            eviction_policy=EvictionPolicy.LRU,
        )
        e1 = mgr.create(project="t", provider="g", model="m", token_count=100)
        time.sleep(0.01)
        e2 = mgr.create(project="t", provider="g", model="m", token_count=200)

        # Access e1 to make it recently used
        mgr.get(e1.cache_id)
        time.sleep(0.01)

        # This should evict e2 (least recently used)
        e3 = mgr.create(project="t", provider="g", model="m", token_count=300)

        assert mgr.get(e1.cache_id) is not None
        assert mgr.get(e2.cache_id) is None
        assert mgr.get(e3.cache_id) is not None

    def test_stats(self):
        mgr = ContextCacheManager()
        mgr.create(project="alpha", provider="gemini", model="m", token_count=1000)
        mgr.create(project="alpha", provider="openai", model="m", token_count=2000)
        mgr.create(project="beta", provider="gemini", model="m", token_count=3000)

        # Generate a miss
        mgr.get("nonexistent")

        stats = mgr.stats()
        assert stats.total_entries == 3
        assert stats.total_tokens_cached == 6000
        assert stats.by_provider.get("gemini") == 2
        assert stats.by_provider.get("openai") == 1
        assert stats.by_project.get("alpha") == 2

    def test_cleanup_expired(self):
        mgr = ContextCacheManager()
        mgr.create(project="t", provider="g", model="m", token_count=100, ttl_seconds=-1)
        mgr.create(project="t", provider="g", model="m", token_count=200, ttl_seconds=3600)

        cleaned = mgr.cleanup_expired()
        assert cleaned == 1
        assert mgr.stats().total_entries == 1
