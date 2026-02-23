"""
CORTEX v5.2 — L2 Vector Store Tests.

Tests for VectorStoreL2, AsyncEncoder, and MemoryEntry.
Uses a mock embedder to avoid loading the real SentenceTransformer model.
"""

from __future__ import annotations

import pytest

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.models import MemoryEntry
from cortex.memory.vector_store import VectorStoreL2

# ─── Mock Embedder ────────────────────────────────────────────────────


class MockEmbedder:
    """Deterministic mock embedder for testing (no ML model needed)."""

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(text, list):
            return self.embed_batch(text)
        return self._text_to_vector(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        return [self._text_to_vector(t) for t in texts]

    def _text_to_vector(self, text: str) -> list[float]:
        """Generate a deterministic 384-dim vector from text hash."""
        h = hash(text) & 0xFFFFFFFF
        base = [(h >> i & 0xFF) / 255.0 for i in range(0, 32)]
        # Repeat to fill 384 dims
        vec = (base * 12)[:384]
        # Normalize
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm if norm > 0 else 0.0 for v in vec]

    @property
    def dimension(self) -> int:
        return 384


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_encoder():
    """AsyncEncoder backed by a deterministic mock (no ML model)."""
    return AsyncEncoder(embedder=MockEmbedder())


@pytest.fixture
async def store(mock_encoder, tmp_path):
    """VectorStoreL2 with ephemeral temp directory."""
    s = VectorStoreL2(encoder=mock_encoder, db_path=str(tmp_path / "vectors"))
    await s.ensure_collection()
    yield s
    await s.close()


# ─── MemoryEntry Tests ────────────────────────────────────────────────


class TestMemoryEntry:
    def test_creates_with_defaults(self):
        entry = MemoryEntry(content="SQLite WAL prevents lock cascade")
        assert entry.content == "SQLite WAL prevents lock cascade"
        assert entry.source == "episodic"
        assert entry.project is None
        assert len(entry.id) == 32  # hex UUID

    def test_to_payload(self):
        entry = MemoryEntry(
            content="test",
            project="cortex",
            source="fact",
        )
        payload = entry.to_payload()
        assert payload["content"] == "test"
        assert payload["project"] == "cortex"
        assert payload["source"] == "fact"
        assert "created_at" in payload


# ─── VectorStoreL2 Tests ─────────────────────────────────────────────


class TestVectorStoreL2:
    async def test_memorize_and_recall(self, store):
        """Full cycle: memorize a text, recall by semantic similarity."""
        entry = MemoryEntry(content="SQLite WAL mode prevents lock cascade hangs")
        await store.memorize(entry)

        results = await store.recall("database locking issues")
        assert len(results) >= 1
        assert results[0]["content"] == entry.content

    async def test_recall_returns_ordered_by_score(self, store):
        """Results should be ordered by score descending."""
        entries = [
            MemoryEntry(content="Python async event loop optimization"),
            MemoryEntry(content="Rust memory safety guarantees"),
            MemoryEntry(content="JavaScript promise chains"),
        ]
        for e in entries:
            await store.memorize(e)

        results = await store.recall("async programming", limit=3)
        assert len(results) >= 1
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_recall_filters_by_project(self, store):
        """Project filter should only return matching entries."""
        await store.memorize(MemoryEntry(content="Auth flow redesign", project="naroa"))
        await store.memorize(MemoryEntry(content="Auth middleware refactor", project="cortex"))

        results = await store.recall("authentication", project="cortex")
        for r in results:
            assert r["project"] == "cortex"

    async def test_memorize_batch(self, store):
        """Batch insert should store all entries."""
        entries = [MemoryEntry(content=f"Memory entry {i}", project="test") for i in range(10)]
        count = await store.memorize_batch(entries)
        assert count == 10

        total = await store.count()
        assert total == 10

    async def test_forget_removes_entry(self, store):
        """forget(id) should remove the point from Qdrant."""
        entry = MemoryEntry(content="Temporary knowledge")
        await store.memorize(entry)

        assert await store.count() == 1
        await store.forget(entry.id)
        assert await store.count() == 0

    async def test_count_returns_total(self, store):
        """count() should reflect the exact number of stored entries."""
        assert await store.count() == 0

        await store.memorize(MemoryEntry(content="First"))
        assert await store.count() == 1

        await store.memorize(MemoryEntry(content="Second"))
        assert await store.count() == 2

    async def test_empty_store_returns_empty(self, store):
        """recall() on an empty store should return []."""
        results = await store.recall("anything")
        assert results == []

    async def test_ensure_collection_idempotent(self, store):
        """Calling ensure_collection() twice should not fail or duplicate."""
        await store.ensure_collection()
        await store.ensure_collection()
        # If we get here without error, it's idempotent
        assert await store.count() == 0


# ─── AsyncEncoder Tests ──────────────────────────────────────────────


class TestAsyncEncoder:
    async def test_encode_returns_384_dim(self, mock_encoder):
        """Encode should return a 384-dimensional vector."""
        vec = await mock_encoder.encode("test input")
        assert len(vec) == 384

    async def test_encode_batch_returns_correct_count(self, mock_encoder):
        """Batch encode should return one vector per input text."""
        texts = ["hello", "world", "test"]
        vecs = await mock_encoder.encode_batch(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    async def test_encode_batch_empty(self, mock_encoder):
        """Empty batch should return []."""
        vecs = await mock_encoder.encode_batch([])
        assert vecs == []

    async def test_dimension_property(self, mock_encoder):
        """dimension should be 384."""
        assert mock_encoder.dimension == 384
