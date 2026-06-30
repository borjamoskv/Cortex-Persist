# [C5-REAL] Exergy-Maximized
"""
Tests for QdrantVectorBackend.
"""

from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")
from unittest.mock import AsyncMock, MagicMock

from babylon60.storage.qdrant import (
    QdrantVectorBackend,
    VectorBackend,
    init_vector_backend,
    get_vector_backend,
)
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PointIdsList,
)


@pytest.mark.asyncio
async def test_qdrant_vector_backend_protocol():
    """Verify QdrantVectorBackend satisfies the VectorBackend protocol at runtime."""
    backend = QdrantVectorBackend()
    assert isinstance(backend, VectorBackend)


def test_qdrant_collection_naming():
    """Verify naming rules and character sanitization for tenant collections."""
    backend = QdrantVectorBackend()
    # Simple tenant
    assert backend._collection_name("default") == "cortex_default"
    # Special characters
    assert backend._collection_name("acme-123!") == "cortex_acme_123_"


@pytest.mark.asyncio
async def test_qdrant_connect_and_close(monkeypatch):
    """Verify that connect initializes client and close clears it."""
    backend = QdrantVectorBackend()

    mock_client_instance = AsyncMock()
    # Mock AsyncQdrantClient constructor to return our mock
    mock_client_class = MagicMock(return_value=mock_client_instance)
    monkeypatch.setattr("qdrant_client.AsyncQdrantClient", mock_client_class)

    await backend.connect()
    assert backend._client is mock_client_instance
    mock_client_class.assert_called_once_with(url=backend.url, api_key=None)

    await backend.close()
    assert backend._client is None
    mock_client_instance.close.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_ensure_collection(monkeypatch):
    """Verify collection creation is called only when it does not exist."""
    backend = QdrantVectorBackend()
    mock_client = AsyncMock()
    backend._client = mock_client

    # Case 1: collection already exists
    mock_client.collection_exists.return_value = True
    await backend._ensure_collection("cortex_test")
    mock_client.collection_exists.assert_called_once_with("cortex_test")
    mock_client.create_collection.assert_not_called()
    assert "cortex_test" in backend._initialized_collections

    # Case 2: cached in _initialized_collections, should not query existence again
    mock_client.collection_exists.reset_mock()
    await backend._ensure_collection("cortex_test")
    mock_client.collection_exists.assert_not_called()

    # Case 3: collection does not exist, create collection
    backend._initialized_collections.clear()
    mock_client.collection_exists.reset_mock()
    mock_client.collection_exists.return_value = False
    await backend._ensure_collection("cortex_test")
    mock_client.collection_exists.assert_called_once_with("cortex_test")
    mock_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_upsert(monkeypatch):
    """Verify upsert maps arguments to PointStruct and calls client."""
    backend = QdrantVectorBackend()
    mock_client = AsyncMock()
    backend._client = mock_client
    # Pre-warm initialized collections to avoid exists calls
    backend._initialized_collections.add("cortex_default")

    await backend.upsert(
        fact_id=42, embedding=[0.1] * 384, tenant_id="default", payload={"project": "cortex"}
    )

    # Check that client.upsert was called with the correct points list
    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args[1]
    assert call_kwargs["collection_name"] == "cortex_default"
    points = call_kwargs["points"]
    assert len(points) == 1
    assert isinstance(points[0], PointStruct)
    assert points[0].id == 42
    assert points[0].vector == [0.1] * 384
    assert points[0].payload == {"project": "cortex"}


@pytest.mark.asyncio
async def test_qdrant_search(monkeypatch):
    """Verify search returns hitting IDs/scores and handles filters."""
    backend = QdrantVectorBackend()
    mock_client = AsyncMock()
    backend._client = mock_client
    backend._initialized_collections.add("cortex_default")

    # Mock search return hits
    class MockHit:
        def __init__(self, id, score):
            self.id = id
            self.score = score

    mock_client.search.return_value = [MockHit(42, 0.95), MockHit(43, 0.88)]

    # 1. Search without project filter
    results = await backend.search([0.1] * 384, top_k=2, tenant_id="default")
    assert results == [(42, 0.95), (43, 0.88)]
    mock_client.search.assert_called_once_with(
        collection_name="cortex_default",
        query_vector=[0.1] * 384,
        limit=2,
        query_filter=None,
        with_payload=False,
    )

    # 2. Search with project filter
    mock_client.search.reset_mock()
    await backend.search([0.1] * 384, top_k=2, tenant_id="default", project="cortex")
    mock_client.search.assert_called_once()
    filter_arg = mock_client.search.call_args[1]["query_filter"]
    assert isinstance(filter_arg, Filter)
    assert len(filter_arg.must) == 1
    cond = filter_arg.must[0]
    assert isinstance(cond, FieldCondition)
    assert cond.key == "project"
    assert cond.match.value == "cortex"


@pytest.mark.asyncio
async def test_qdrant_delete(monkeypatch):
    """Verify delete wraps point IDs list correctly."""
    backend = QdrantVectorBackend()
    mock_client = AsyncMock()
    backend._client = mock_client

    await backend.delete(fact_id=42, tenant_id="default")
    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args[1]
    assert call_kwargs["collection_name"] == "cortex_default"
    assert isinstance(call_kwargs["points_selector"], PointIdsList)
    assert call_kwargs["points_selector"].points == [42]


@pytest.mark.asyncio
async def test_qdrant_health_check():
    """Verify health_check works based on get_collections success/failure."""
    backend = QdrantVectorBackend()
    # Unconnected
    assert await backend.health_check() is False

    # Connected and working
    mock_client = AsyncMock()
    backend._client = mock_client
    mock_client.get_collections.return_value = MagicMock()
    assert await backend.health_check() is True

    # Connection error / Exception
    mock_client.get_collections.side_effect = RuntimeError("Connection lost")
    assert await backend.health_check() is False


@pytest.mark.asyncio
async def test_init_vector_backend(monkeypatch):
    """Verify init_vector_backend correctly reads configuration from environment."""
    # 1. Default (no CORTEX_VECTOR_BACKEND env)
    monkeypatch.delenv("CORTEX_VECTOR_BACKEND", raising=False)
    backend = await init_vector_backend()
    assert backend is None
    assert get_vector_backend() is None

    # 2. Set to qdrant
    monkeypatch.setenv("CORTEX_VECTOR_BACKEND", "qdrant")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant-server:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "secret-api-key")

    mock_backend_instance = AsyncMock(spec=QdrantVectorBackend)
    mock_backend_class = MagicMock(return_value=mock_backend_instance)
    monkeypatch.setattr("cortex.storage.qdrant.QdrantVectorBackend", mock_backend_class)

    res = await init_vector_backend()
    assert res is mock_backend_instance
    assert get_vector_backend() is mock_backend_instance
    mock_backend_class.assert_called_once_with(
        url="http://qdrant-server:6333", api_key="secret-api-key"
    )
    mock_backend_instance.connect.assert_called_once()
