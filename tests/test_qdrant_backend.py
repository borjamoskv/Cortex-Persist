"""
CORTEX v6.0 — Qdrant Backend Integration Tests.

Requires a running Qdrant instance:
    docker run -p 6333:6333 qdrant/qdrant:v1.12.1

Set QDRANT_URL to run. Otherwise auto-skipped.
"""

from __future__ import annotations

import os

import pytest

QDRANT_URL = os.environ.get("QDRANT_URL", "")
pytestmark = pytest.mark.skipif(
    not QDRANT_URL,
    reason="QDRANT_URL not set — skip Qdrant integration tests",
)

DIM = 384


def _random_vec() -> list[float]:
    """Generate a deterministic normalised test vector."""
    import math

    v = [float(i % 10 + 1) for i in range(DIM)]
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


def _alt_vec() -> list[float]:
    """Different vector for diversity tests."""
    import math

    v = [float((i * 7) % 11 + 1) for i in range(DIM)]
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


@pytest.fixture
async def qdrant():
    """Provide a connected QdrantVectorBackend."""
    from cortex.storage.qdrant import QdrantVectorBackend

    backend = QdrantVectorBackend(url=QDRANT_URL)
    await backend.connect()
    yield backend
    # Cleanup test collections
    try:
        client = backend._client
        if client:
            colls = await client.get_collections()
            for c in colls.collections:
                if c.name.startswith("cortex_test_"):
                    await client.delete_collection(c.name)
    except Exception:
        pass
    await backend.close()


@pytest.mark.asyncio
async def test_health_check(qdrant):
    assert await qdrant.health_check() is True


@pytest.mark.asyncio
async def test_upsert_and_search(qdrant):
    """Upsert a vector and retrieve it via search."""
    vec = _random_vec()
    await qdrant.upsert(fact_id=1001, embedding=vec, tenant_id="test_basic")

    results = await qdrant.search(
        query_embedding=vec,
        top_k=1,
        tenant_id="test_basic",
    )
    assert len(results) == 1
    fact_id, score = results[0]
    assert fact_id == 1001
    assert score > 0.99  # should be near-identical (cosine similarity)


@pytest.mark.asyncio
async def test_upsert_idempotent(qdrant):
    """Re-upserting same fact_id should not duplicate."""
    vec = _random_vec()
    await qdrant.upsert(1002, vec, "test_idem")
    await qdrant.upsert(1002, vec, "test_idem")  # duplicate

    results = await qdrant.search(vec, top_k=10, tenant_id="test_idem")
    ids = [r[0] for r in results]
    assert ids.count(1002) == 1


@pytest.mark.asyncio
async def test_project_filter(qdrant):
    """Project filter should exclude non-matching facts."""
    vec_a = _random_vec()
    vec_b = _alt_vec()

    await qdrant.upsert(2001, vec_a, "test_filter", payload={"project": "alpha"})
    await qdrant.upsert(2002, vec_b, "test_filter", payload={"project": "beta"})

    # Search for alpha only
    results = await qdrant.search(vec_a, top_k=5, tenant_id="test_filter", project="alpha")
    ids = [r[0] for r in results]
    assert 2001 in ids
    assert 2002 not in ids


@pytest.mark.asyncio
async def test_delete(qdrant):
    """Deleted vectors should not appear in search."""
    vec = _random_vec()
    await qdrant.upsert(3001, vec, "test_delete")
    await qdrant.delete(3001, "test_delete")

    results = await qdrant.search(vec, top_k=5, tenant_id="test_delete")
    ids = [r[0] for r in results]
    assert 3001 not in ids


@pytest.mark.asyncio
async def test_tenant_isolation(qdrant):
    """Vectors in different tenants should not bleed through."""
    vec = _random_vec()
    await qdrant.upsert(4001, vec, "test_tenant_a")

    # Search in different tenant — should return nothing
    results = await qdrant.search(vec, top_k=5, tenant_id="test_tenant_b_empty")
    assert results == []


@pytest.mark.asyncio
async def test_collection_name_sanitization(qdrant):
    """Tenant IDs with special chars should produce valid collection names."""
    col = qdrant._collection_name("tenant@email.com/slash")
    assert "@" not in col
    assert "." not in col
    assert "/" not in col
    assert col.startswith("cortex_")


@pytest.mark.asyncio
async def test_health_check_fails_after_close(qdrant):
    """After close, health check returns False."""
    await qdrant.close()
    assert await qdrant.health_check() is False


@pytest.mark.asyncio
async def test_search_empty_collection():
    """Searching a non-existent collection returns empty list, not error."""
    from cortex.storage.qdrant import QdrantVectorBackend

    backend = QdrantVectorBackend(url=QDRANT_URL)
    await backend.connect()
    try:
        results = await backend.search(
            _random_vec(),
            top_k=5,
            tenant_id="test_nonexistent_tenant_xyz",
        )
        assert results == []
    finally:
        await backend.close()


@pytest.mark.asyncio
async def test_vector_backend_protocol():
    """QdrantVectorBackend should satisfy the VectorBackend protocol."""
    from cortex.storage.qdrant import QdrantVectorBackend, VectorBackend

    backend = QdrantVectorBackend(url=QDRANT_URL)
    assert isinstance(backend, VectorBackend)
