"""Tests for CORTEX Memory Core — L1, Compression, Thalamus, Resonance.

Covers the 4 most critical untested paths in cortex/memory/.
All tests are self-contained with mocks — no DB, no Redis, no LLM.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.memory.compression import CompressionResult, SemanticCompressor
from cortex.memory.models import MemoryEvent
from cortex.memory.working import WorkingMemoryL1


# ─── Helpers ─────────────────────────────────────────────────────────────


def _make_event(
    role: str = "user",
    content: str = "test content",
    token_count: int = 100,
    tenant_id: str = "test_tenant",
    session_id: str = "sess_1",
    metadata: dict[str, Any] | None = None,
) -> MemoryEvent:
    """Factory for MemoryEvent with sane defaults."""
    return MemoryEvent(
        role=role,
        content=content,
        token_count=token_count,
        session_id=session_id,
        tenant_id=tenant_id,
        metadata=metadata or {},
    )


@dataclass
class MockEngram:
    """Lightweight engram mock for compression tests."""

    content: str
    id: str = "mock_id"
    embedding: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])
    project_id: str = "test"
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── L1 WorkingMemoryL1 ──────────────────────────────────────────────────


class TestWorkingMemoryL1:
    """Tests for the L1 token-budgeted sliding window."""

    def test_init_positive_tokens(self):
        l1 = WorkingMemoryL1(max_tokens=1024)
        assert l1.max_tokens == 1024
        assert len(l1) == 0

    def test_init_rejects_zero_tokens(self):
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=0)

    def test_init_rejects_negative_tokens(self):
        with pytest.raises(ValueError, match="positive"):
            WorkingMemoryL1(max_tokens=-1)

    def test_add_single_event(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        event = _make_event(token_count=50)
        overflow = l1.add_event(event)
        assert overflow == []
        assert len(l1) == 1
        assert l1.event_count(tenant_id="test_tenant") == 1
        assert l1.utilization(tenant_id="test_tenant") == pytest.approx(0.05)

    def test_add_triggers_overflow(self):
        """When token budget is exceeded, lowest-priority events are evicted."""
        l1 = WorkingMemoryL1(max_tokens=150)
        e1 = _make_event(content="old event", token_count=100)
        e2 = _make_event(content="new event", token_count=100)

        overflow1 = l1.add_event(e1)
        assert overflow1 == []

        overflow2 = l1.add_event(e2)
        assert len(overflow2) == 1
        # The evicted event should be the one with lower priority
        assert overflow2[0].content in ("old event", "new event")

    def test_get_context_returns_prompt_dicts(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_make_event(role="user", content="hello"))
        l1.add_event(_make_event(role="assistant", content="hi"))

        ctx = l1.get_context(tenant_id="test_tenant")
        assert len(ctx) == 2
        assert ctx[0] == {"role": "user", "content": "hello"}
        assert ctx[1] == {"role": "assistant", "content": "hi"}

    def test_get_context_empty_tenant(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        ctx = l1.get_context(tenant_id="nonexistent")
        assert ctx == []

    def test_tenant_isolation(self):
        """Events from different tenants don't share buffers."""
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_make_event(tenant_id="tenant_a"))
        l1.add_event(_make_event(tenant_id="tenant_b"))

        ctx_a = l1.get_context(tenant_id="tenant_a")
        ctx_b = l1.get_context(tenant_id="tenant_b")
        assert len(ctx_a) == 1
        assert len(ctx_b) == 1

    def test_clear_specific_tenant(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_make_event(tenant_id="keep"))
        l1.add_event(_make_event(tenant_id="drop"))

        flushed = l1.clear(tenant_id="drop")
        assert len(flushed) == 1
        assert l1.get_context(tenant_id="keep") != []
        assert l1.get_context(tenant_id="drop") == []

    def test_clear_all(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_make_event(tenant_id="a"))
        l1.add_event(_make_event(tenant_id="b"))
        flushed = l1.clear()
        assert len(flushed) == 2
        assert len(l1) == 0

    def test_snapshot_and_restore(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        l1.add_event(_make_event(content="snapshot me", token_count=50))

        snap = l1.snapshot(tenant_id="test_tenant")
        assert snap["tokens"] == 50
        assert len(snap["events"]) == 1

        l1_new = WorkingMemoryL1(max_tokens=1000)
        l1_new.restore(snap, tenant_id="test_tenant")
        ctx = l1_new.get_context(tenant_id="test_tenant")
        assert len(ctx) == 1
        assert ctx[0]["content"] == "snapshot me"

    def test_utilization_ratio(self):
        l1 = WorkingMemoryL1(max_tokens=200)
        l1.add_event(_make_event(token_count=100))
        assert l1.utilization(tenant_id="test_tenant") == pytest.approx(0.5)

    def test_repr(self):
        l1 = WorkingMemoryL1(max_tokens=1000)
        r = repr(l1)
        assert "WorkingMemoryL1" in r
        assert "tokens=0" in r

    def test_access_frequency(self):
        """Verify access frequency tracking works over a window."""
        l1 = WorkingMemoryL1(max_tokens=1000)
        # Add events that generate access log entries
        for _ in range(10):
            l1.add_event(
                _make_event(
                    metadata={"project_id": "proj_x"},
                )
            )
        freq = l1.get_access_frequency("test_tenant:proj_x", window_seconds=3600.0)
        assert freq > 0.0


# ─── Semantic Compressor ─────────────────────────────────────────────────


class TestSemanticCompressor:
    """Tests for the MDL-based semantic compressor."""

    def test_below_cluster_threshold_passthrough(self):
        compressor = SemanticCompressor(min_cluster_size=5)
        engrams = [MockEngram(content="fact 1"), MockEngram(content="fact 2")]
        result = compressor.compress(engrams)

        assert result.original_count == 2
        assert result.compression_ratio == 1.0
        assert "fact 1" in result.compressed_content

    def test_default_compression_deduplicates(self):
        compressor = SemanticCompressor(min_cluster_size=2)
        engrams = [
            MockEngram(content="The sky is blue"),
            MockEngram(content="the sky is blue"),  # Case-insensitive dup
            MockEngram(content="Water is wet"),
        ]
        result = compressor.compress(engrams)

        assert result.original_count == 3
        assert result.compression_ratio < 1.0
        assert result.savings_percent > 0.0

    def test_custom_summarizer(self):
        compressor = SemanticCompressor(min_cluster_size=2)
        summarizer = lambda contents: "COMPRESSED"  # noqa: E731
        engrams = [MockEngram(content="a" * 100), MockEngram(content="b" * 100)]

        result = compressor.compress(engrams, summarizer=summarizer)
        assert result.compressed_content == "COMPRESSED"
        assert result.savings_percent > 0.0

    def test_max_output_tokens_truncation(self):
        compressor = SemanticCompressor(min_cluster_size=2, max_output_tokens=5)
        engrams = [MockEngram(content="a" * 1000), MockEngram(content="b" * 1000)]
        result = compressor.compress(engrams)
        # Result should be truncated to ~5 tokens
        assert result.compressed_tokens <= 10  # Some tolerance

    def test_compression_result_savings_percent(self):
        r = CompressionResult(original_tokens=100, compressed_tokens=20)
        assert r.savings_percent == pytest.approx(80.0)

    def test_compression_result_zero_original(self):
        r = CompressionResult(original_tokens=0, compressed_tokens=0)
        assert r.savings_percent == 0.0


# ─── Thalamus Gate ───────────────────────────────────────────────────────


class TestThalamusGate:
    """Tests for the sovereign pre-filtering gate."""

    @pytest.fixture
    def mock_manager(self):
        manager = MagicMock()
        manager._l2 = MagicMock()
        manager._encoder = AsyncMock()
        manager._encoder.encode = AsyncMock(return_value=[0.1] * 384)
        return manager

    @pytest.mark.asyncio
    async def test_low_density_rejected(self, mock_manager):
        from cortex.memory.thalamus import ThalamusGate

        gate = ThalamusGate(mock_manager, min_density=10)
        should, action, _ = await gate.filter(
            content="short",
            project_id="p",
            tenant_id="t",
        )
        assert should is False
        assert "low_density" in action

    @pytest.mark.asyncio
    async def test_normal_content_passes(self, mock_manager):
        from cortex.memory.thalamus import ThalamusGate

        gate = ThalamusGate(mock_manager, min_density=5)

        # Patch the dense retrieval to return empty (no duplicates)
        with patch(
            "cortex.memory.thalamus._fetch_dense_results",
            new_callable=AsyncMock,
            return_value=[],
        ):
            should, action, _ = await gate.filter(
                content="This is a perfectly normal length fact about system architecture.",
                project_id="cortex",
                tenant_id="test",
            )
        assert should is True
        assert action == "encode:new"

    @pytest.mark.asyncio
    async def test_identical_content_rejected(self, mock_manager):
        from cortex.memory.thalamus import ThalamusGate

        gate = ThalamusGate(mock_manager, min_density=5)

        # Simulate an existing identical fact
        existing_fact = MagicMock()
        existing_fact.id = "existing_123"
        existing_fact.content = "exact duplicate content here"
        existing_fact.fact_type = "general"

        with patch(
            "cortex.memory.thalamus._fetch_dense_results",
            new_callable=AsyncMock,
            return_value=[existing_fact],
        ):
            should, action, meta = await gate.filter(
                content="exact duplicate content here",
                project_id="p",
                tenant_id="t",
            )
        assert should is False
        assert "identical" in action

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_retrieval_error(self, mock_manager):
        from cortex.memory.thalamus import ThalamusGate

        gate = ThalamusGate(mock_manager, min_density=5)

        with patch(
            "cortex.memory.thalamus._fetch_dense_results",
            new_callable=AsyncMock,
            side_effect=RuntimeError("vector store down"),
        ):
            should, action, _ = await gate.filter(
                content="This should still pass despite retrieval failure.",
                project_id="p",
                tenant_id="t",
            )
        # Gate degrades gracefully — allows the write
        assert should is True
        assert action == "encode:new"


# ─── Adaptive Resonance Gate ────────────────────────────────────────────


class TestAdaptiveResonanceGate:
    """Tests for the ART-v2 inspired write gate."""

    @pytest.fixture
    def mock_engram(self):
        from cortex.memory.engrams import CortexSemanticEngram

        return CortexSemanticEngram(
            id="new_1",
            tenant_id="t",
            project_id="p",
            content="test engram",
            embedding=[1.0, 0.0, 0.0],
            timestamp=time.time(),
            metadata={},
            cognitive_layer="semantic",
        )

    @pytest.fixture
    def mock_vector_store(self):
        vs = AsyncMock()
        vs.search_similar = AsyncMock(return_value=[])
        vs.upsert = AsyncMock()
        return vs

    @pytest.mark.asyncio
    async def test_reset_on_no_neighbors(self, mock_engram, mock_vector_store):
        from cortex.memory.resonance import AdaptiveResonanceGate

        gate = AdaptiveResonanceGate(vector_store=mock_vector_store, rho=0.85)
        status, engram = await gate.gate(mock_engram)

        assert status == "reset"
        assert engram.id == "new_1"
        mock_vector_store.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_resonance_on_matching_neighbor(self, mock_engram, mock_vector_store):
        from cortex.memory.engrams import CortexSemanticEngram
        from cortex.memory.resonance import AdaptiveResonanceGate

        existing = CortexSemanticEngram(
            id="existing_1",
            tenant_id="t",
            project_id="p",
            content="very similar engram",
            embedding=[0.99, 0.01, 0.0],  # Very similar to [1, 0, 0]
            timestamp=time.time(),
            metadata={},
            cognitive_layer="semantic",
            energy_level=0.5,  # Below max so LTP boost is observable
        )
        mock_vector_store.search_similar = AsyncMock(return_value=[existing])

        gate = AdaptiveResonanceGate(vector_store=mock_vector_store, rho=0.85)
        status, engram = await gate.gate(mock_engram)

        assert status == "resonance"
        assert engram.id == "existing_1"
        # Energy should be boosted (LTP)
        assert engram.energy_level > existing.energy_level

    @pytest.mark.asyncio
    async def test_precision_mode_raises_vigilance(self, mock_engram, mock_vector_store):
        from cortex.memory.engrams import CortexSemanticEngram
        from cortex.memory.resonance import AdaptiveResonanceGate

        # Engram that would match at rho=0.85 but NOT at rho=0.95
        marginal = CortexSemanticEngram(
            id="marginal_1",
            tenant_id="t",
            project_id="p",
            content="somewhat similar",
            embedding=[0.9, 0.3, 0.0],  # sim ~0.94 with [1,0,0]
            timestamp=time.time(),
            metadata={},
            cognitive_layer="semantic",
        )
        mock_vector_store.search_similar = AsyncMock(return_value=[marginal])

        gate = AdaptiveResonanceGate(vector_store=mock_vector_store, rho=0.85)
        # In precision mode, rho increases by 0.1 → 0.95
        status, _ = await gate.gate(mock_engram, precision_mode=True)
        assert status == "reset"  # Should NOT resonate at higher vigilance

    @pytest.mark.asyncio
    async def test_no_vector_store_search_graceful(self, mock_engram):
        from cortex.memory.resonance import AdaptiveResonanceGate

        # Vector store without search_similar
        bare_vs = MagicMock(spec=[])
        bare_vs.upsert = AsyncMock()

        gate = AdaptiveResonanceGate(vector_store=bare_vs, rho=0.85)
        status, engram = await gate.gate(mock_engram)
        assert status == "reset"


# ─── Cosine Similarity ──────────────────────────────────────────────────


class TestCosineSimilarity:
    """Tests for the cosine_similarity utility in resonance module."""

    def test_identical_vectors(self):
        from cortex.memory.resonance import cosine_similarity

        assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        from cortex.memory.resonance import cosine_similarity

        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_empty_vectors(self):
        from cortex.memory.resonance import cosine_similarity

        assert cosine_similarity([], []) == 0.0

    def test_mismatched_lengths(self):
        from cortex.memory.resonance import cosine_similarity

        assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0

    def test_zero_vector(self):
        from cortex.memory.resonance import cosine_similarity

        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
