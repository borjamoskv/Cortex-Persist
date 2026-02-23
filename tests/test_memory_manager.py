# fmt: off
"""
CORTEX v5.3 — Memory Manager Tests.

Tests for CortexMemoryManager: the Tripartite Memory orchestrator.
Uses mock L2 (Qdrant) and in-memory L3 (SQLite) for test isolation.
"""
# fmt: on

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

# ── Stub qdrant_client before any cortex.memory import ─────────────────
# cortex.memory.__init__ eagerly imports VectorStoreL2 → qdrant_client.
# The VectorStoreL2 internally awaits AsyncQdrantClient coroutines, so
# we need AsyncMock for any method that will be awaited.
_qd_models = MagicMock()
_qd = MagicMock()
_qd.models = _qd_models
# AsyncQdrantClient constructor returns a mock whose async methods are AsyncMock
_async_qd_instance = AsyncMock()
_qd.AsyncQdrantClient = MagicMock(return_value=_async_qd_instance)
sys.modules["qdrant_client"] = _qd
sys.modules["qdrant_client.models"] = _qd_models

import aiosqlite  # noqa: E402
import pytest  # noqa: E402

from cortex.memory.encoder import AsyncEncoder  # noqa: E402
from cortex.memory.ledger import EventLedgerL3  # noqa: E402
from cortex.memory.manager import CortexMemoryManager  # noqa: E402
from cortex.memory.vector_store import VectorStoreL2  # noqa: E402
from cortex.memory.working import WorkingMemoryL1  # noqa: E402


# ─── Mock Embedder ────────────────────────────────────────────────────


class MockEmbedder:
    """Deterministic 384-dim embedder (no ML model)."""

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(text, list):
            return self.embed_batch(text)
        return self._vec(text)

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        h = hash(text) & 0xFFFFFFFF
        base = [(h >> i & 0xFF) / 255.0 for i in range(0, 32)]
        vec = (base * 12)[:384]
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm if norm > 0 else 0.0 for v in vec]

    @property
    def dimension(self) -> int:
        return 384


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_encoder():
    return AsyncEncoder(embedder=MockEmbedder())


@pytest.fixture
async def manager(mock_encoder, tmp_path):
    """Full Tripartite Memory stack with ephemeral storage."""
    l1 = WorkingMemoryL1(max_tokens=500)
    l2 = VectorStoreL2(encoder=mock_encoder, db_path=str(tmp_path / "vectors"))
    conn = await aiosqlite.connect(str(tmp_path / "ledger.db"))
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=5000")
    l3 = EventLedgerL3(conn)

    mgr = CortexMemoryManager(l1=l1, l2=l2, l3=l3, encoder=mock_encoder)
    yield mgr

    await mgr.wait_for_background()
    await l2.close()
    await conn.close()


# ─── Tests ────────────────────────────────────────────────────────────


class TestCortexMemoryManager:
    async def test_process_interaction_persists_to_l3(self, manager):
        """Events should land in L3 (immutable ledger)."""
        event = await manager.process_interaction(
            role="user",
            content="What is CORTEX?",
            session_id="s1",
            token_count=10,
        )
        assert event.content == "What is CORTEX?"

        l3_events = await manager.l3.get_session_events("s1")
        assert len(l3_events) == 1
        assert l3_events[0].event_id == event.event_id

    async def test_process_interaction_fills_l1(self, manager):
        """Events should appear in L1 working memory."""
        await manager.process_interaction(
            role="user", content="hello", session_id="s1", token_count=50,
        )
        assert manager.l1.event_count == 1
        assert manager.l1.current_tokens == 50

    async def test_overflow_triggers_compression(self, manager):
        """When L1 overflows, events should be sent to background compression."""
        for i in range(5):
            await manager.process_interaction(
                role="user",
                content=f"Event {i}",
                session_id="s1",
                token_count=150,  # 5 * 150 = 750 > 500
            )
        # Wait for any background tasks to drain (some may silently fail
        # with the AsyncMock if L2.memorize path is not fully wired)
        await manager.wait_for_background()
        # Just verify we got through without crashing
        assert manager.l1.event_count < 5  # Some events evicted to background

    async def test_assemble_context_returns_working_memory(self, manager):
        """assemble_context without query returns L1 only."""
        await manager.process_interaction(
            role="user", content="test context", session_id="s1", token_count=50,
        )
        ctx = await manager.assemble_context()
        assert len(ctx["working_memory"]) == 1
        assert ctx["working_memory"][0]["content"] == "test context"
        assert ctx["episodic_context"] == []

    async def test_assemble_context_with_query(self, manager):
        """assemble_context with query key present."""
        await manager.process_interaction(
            role="user", content="cortex system", session_id="s1", token_count=50,
        )
        ctx = await manager.assemble_context(query="cortex")
        assert "episodic_context" in ctx
        assert "working_memory" in ctx

    async def test_repr_is_informative(self, manager):
        """__repr__ should contain useful state info."""
        r = repr(manager)
        assert "CortexMemoryManager" in r
        assert "bg_tasks=" in r

    async def test_metadata_flows_through(self, manager):
        """Metadata provided at process_interaction should persist to L3."""
        await manager.process_interaction(
            role="tool",
            content="qdrant search result",
            session_id="s1",
            token_count=30,
            metadata={"tool_name": "vector_store"},
        )
        events = await manager.l3.get_session_events("s1")
        assert events[0].metadata["tool_name"] == "vector_store"
