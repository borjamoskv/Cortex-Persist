# [C5-REAL] Exergy-Maximized
"""
Unit and integration tests for L1/L2 Cache Coherence.
Verifies read cache lookup, write cache invalidation, and tenant isolation.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

from babylon60.engine import CortexEngine
from babylon60.cache.redis_l1 import RedisL1Cache
from babylon60.search.models import SearchResult

# Mark tests as slow due to CortexEngine DB initialization
pytestmark = pytest.mark.slow


class MockRedis:
    def __init__(self):
        self.store = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    def keys(self, pattern):
        # simple pattern matching: search:* -> prefix matches
        prefix = pattern.replace("*", "")
        return [k for k in self.store if k.startswith(prefix)]

    def info(self, section=None):
        return {"used_memory": 1024, "used_memory_human": "1K"}


@pytest.fixture
def mock_redis_client():
    mock_client = MockRedis()

    # We patch the RedisL1Cache singleton instance
    cache = RedisL1Cache(host="127.0.0.1", port=6379, db=0, _client=mock_client)

    with patch.object(RedisL1Cache, "singleton", return_value=cache):
        yield mock_client


@pytest.fixture
async def engine(tmp_path: Path, monkeypatch):
    import os

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    db = str(tmp_path / "test_cache.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    from babylon60.engine.flow.causality import AsyncCausalGraph

    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
        await cg.ensure_table()

    yield e
    await e.close()


@pytest.mark.asyncio
async def test_search_cache_aside_flow(engine, mock_redis_client):
    # 1. Initially, cache is empty
    assert len(mock_redis_client.store) == 0

    # Store a test fact
    fact_id = await engine.store(
        project="test_proj",
        content="The cache coherence is crucial for agent memory consistency.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-alpha",
    )

    # 2. First search - Cache Miss
    results1 = await engine.search(
        query="cache coherence", tenant_id="tenant-alpha", project="test_proj"
    )
    assert len(results1) > 0
    assert any(r.fact_id == fact_id for r in results1)

    # Cache should now contain the serialized results
    assert len(mock_redis_client.store) == 1
    cache_key = list(mock_redis_client.store.keys())[0]
    assert "tenant-alpha" in cache_key

    # 3. Second search - Cache Hit
    # We alter the DB content or modify the cached representation in Redis to verify the hit
    cached_val = mock_redis_client.store[cache_key]
    data = json.loads(cached_val.decode("utf-8"))
    assert len(data) > 0
    data[0]["content"] = "CACHED_CONTENT_HIT"
    mock_redis_client.store[cache_key] = json.dumps(data).encode("utf-8")

    results2 = await engine.search(
        query="cache coherence", tenant_id="tenant-alpha", project="test_proj"
    )
    assert len(results2) > 0
    assert results2[0].content == "CACHED_CONTENT_HIT"


@pytest.mark.asyncio
async def test_write_invalidates_cache(engine, mock_redis_client):
    # Store a fact and trigger search to populate cache
    await engine.store(
        project="test_proj",
        content="Coherence target.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-beta",
    )

    await engine.search(query="Coherence target", tenant_id="tenant-beta", project="test_proj")
    assert len(mock_redis_client.store) > 0

    # Store a new fact under the same tenant -> Cache should be flushed
    await engine.store(
        project="test_proj",
        content="Another fact invalidates cache.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-beta",
    )

    # Verify the cache for tenant-beta is cleared
    assert len(mock_redis_client.store) == 0


@pytest.mark.asyncio
async def test_update_invalidates_cache(engine, mock_redis_client):
    fact_id = await engine.store(
        project="test_proj",
        content="Original fact.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-gamma",
    )

    await engine.search(query="Original fact", tenant_id="tenant-gamma", project="test_proj")
    assert len(mock_redis_client.store) > 0

    # Update the fact -> Cache should be flushed
    await engine.update(fact_id=fact_id, content="Updated fact content.", tenant_id="tenant-gamma")

    assert len(mock_redis_client.store) == 0


@pytest.mark.asyncio
async def test_deprecate_invalidates_cache(engine, mock_redis_client):
    fact_id = await engine.store(
        project="test_proj",
        content="Fact to deprecate.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-delta",
    )

    await engine.search(query="Fact to deprecate", tenant_id="tenant-delta", project="test_proj")
    assert len(mock_redis_client.store) > 0

    # Deprecate the fact -> Cache should be flushed
    await engine.deprecate(fact_id=fact_id, reason="outdated", tenant_id="tenant-delta")

    assert len(mock_redis_client.store) == 0


@pytest.mark.asyncio
async def test_invalidate_and_purge_invalidate_cache(engine, mock_redis_client):
    fact_id = await engine.store(
        project="test_proj",
        content="Fact to invalidate.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-epsilon",
    )

    await engine.search(query="Fact to invalidate", tenant_id="tenant-epsilon", project="test_proj")
    assert len(mock_redis_client.store) > 0

    # Invalidate the fact -> Cache should be flushed
    await engine.invalidate(fact_id=fact_id, reason="incorrect", tenant_id="tenant-epsilon")
    assert len(mock_redis_client.store) == 0

    # Search again to populate cache
    await engine.search(query="Fact to invalidate", tenant_id="tenant-epsilon", project="test_proj")
    assert len(mock_redis_client.store) > 0

    # Purge the fact -> Cache should be flushed
    await engine.purge(fact_id=fact_id, tenant_id="tenant-epsilon", force=True)
    assert len(mock_redis_client.store) == 0


@pytest.mark.asyncio
async def test_tenant_cache_isolation(engine, mock_redis_client):
    # Store and cache for tenant-A
    await engine.store(
        project="test_proj",
        content="Tenant A content.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-a",
    )
    await engine.search(query="Tenant A content", tenant_id="tenant-a", project="test_proj")

    # Store and cache for tenant-B
    await engine.store(
        project="test_proj",
        content="Tenant B content.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-b",
    )
    await engine.search(query="Tenant B content", tenant_id="tenant-b", project="test_proj")

    # We should have both cached keys in the store
    assert len(mock_redis_client.store) == 2

    # Mutating tenant-A should flush only tenant-a, leaving tenant-b untouched
    await engine.store(
        project="test_proj",
        content="New Tenant A write.",
        fact_type="knowledge",
        confidence="C5",
        source="agent:test_suite",
        tenant_id="tenant-a",
    )

    # Verify tenant-b cache key is still present, while tenant-a cache key is gone
    remaining_keys = list(mock_redis_client.store.keys())
    assert any("tenant-b" in k for k in remaining_keys)
    assert not any("tenant-a" in k for k in remaining_keys)
