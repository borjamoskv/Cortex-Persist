"""Tests for Memory OS modules (RFC-CORTEX-MEMORY-OS).

Covers: Mem0Pipeline, MemoryOS, HiAgentTraceManager.
"""

from __future__ import annotations

import pytest

from cortex.compaction.mem0_pipeline import ExergyScore, Mem0Pipeline
from cortex.context.hiagent import HiAgentTraceManager
from cortex.policy.memory_os import MemoryOS, MemoryTier

# ─── Mem0Pipeline ────────────────────────────────────────────────────


class TestMem0Pipeline:
    """Mem0 thermodynamic filter tests."""

    @pytest.fixture
    def pipeline(self) -> Mem0Pipeline:
        return Mem0Pipeline(exergy_threshold=0.5)

    @pytest.mark.asyncio
    async def test_extract_returns_list(self, pipeline: Mem0Pipeline):
        result = await pipeline.extract("some context")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_consolidate_passthrough(self, pipeline: Mem0Pipeline):
        facts = [{"key": "val"}]
        result = await pipeline.consolidate(facts)
        assert result == facts

    @pytest.mark.asyncio
    async def test_evaluate_exergy_default(self, pipeline: Mem0Pipeline):
        score = await pipeline.evaluate_exergy({"content": "test"})
        assert isinstance(score, ExergyScore)
        assert score.score >= 0.0

    @pytest.mark.asyncio
    async def test_store_filters_low_exergy(self, pipeline: Mem0Pipeline):
        pipeline.exergy_threshold = 999.0  # Nothing passes
        stored = await pipeline.store([{"content": "test"}])
        assert stored == 0

    @pytest.mark.asyncio
    async def test_process_full_pipeline(self, pipeline: Mem0Pipeline):
        count = await pipeline.process("some episodic context")
        assert isinstance(count, int)
        assert count >= 0

    def test_exergy_dataclass(self):
        s = ExergyScore(score=0.75, justification="High utility")
        assert s.score == 0.75
        assert s.justification == "High utility"


# ─── MemoryOS ────────────────────────────────────────────────────────


class TestMemoryOS:
    """Memory OS hypervisor tests."""

    @pytest.fixture
    def os(self) -> MemoryOS:
        return MemoryOS()

    @pytest.mark.asyncio
    async def test_write_working_memory(self, os: MemoryOS):
        result = await os.write(MemoryTier.WORKING, "key1", "value1", 1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_write_episodic_memory(self, os: MemoryOS):
        result = await os.write(MemoryTier.EPISODIC, "key1", "value1", 1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_write_semantic_raises(self, os: MemoryOS):
        """Semantic writes must pass through mem0_pipeline."""
        with pytest.raises(NotImplementedError):
            await os.write(MemoryTier.SEMANTIC, "key1", "value1", 1.0)

    @pytest.mark.asyncio
    async def test_read_returns_none_placeholder(self, os: MemoryOS):
        result = await os.read(MemoryTier.WORKING, "query")
        assert result is None

    @pytest.mark.asyncio
    async def test_flush_working(self, os: MemoryOS):
        await os.write(MemoryTier.WORKING, "a", "b", 1.0)
        await os.flush(MemoryTier.WORKING)
        assert os._working_memory == {}

    @pytest.mark.asyncio
    async def test_flush_episodic(self, os: MemoryOS):
        await os.write(MemoryTier.EPISODIC, "a", "b", 1.0)
        await os.flush(MemoryTier.EPISODIC)
        assert os._episodic_traces == []

    @pytest.mark.asyncio
    async def test_flush_semantic_denied(self, os: MemoryOS):
        """Immutable ledger cannot be flushed."""
        with pytest.raises(PermissionError):
            await os.flush(MemoryTier.SEMANTIC)

    def test_memory_tier_values(self):
        assert MemoryTier.WORKING.value == "working"
        assert MemoryTier.EPISODIC.value == "episodic"
        assert MemoryTier.SEMANTIC.value == "semantic"


# ─── HiAgentTraceManager ────────────────────────────────────────────


class TestHiAgentTraceManager:
    """HiAgent subgoal compression tests."""

    @pytest.fixture
    def trace_mgr(self) -> HiAgentTraceManager:
        return HiAgentTraceManager()

    def test_record_step(self, trace_mgr: HiAgentTraceManager):
        trace_mgr.record_step("action1", "observation1")
        assert len(trace_mgr.current_trace) == 1
        assert trace_mgr.current_trace[0]["action"] == "action1"

    @pytest.mark.asyncio
    async def test_compress_subgoal_returns_crystal(
        self, trace_mgr: HiAgentTraceManager
    ):
        trace_mgr.record_step("a1", "o1")
        trace_mgr.record_step("a2", "o2")
        crystal = await trace_mgr.compress_subgoal("test_goal")
        assert crystal["goal"] == "test_goal"
        assert "crystal" in crystal

    @pytest.mark.asyncio
    async def test_compress_flushes_trace(
        self, trace_mgr: HiAgentTraceManager
    ):
        """Amnesia Local: trace must be empty after compression."""
        trace_mgr.record_step("a1", "o1")
        await trace_mgr.compress_subgoal("test_goal")
        assert len(trace_mgr.current_trace) == 0

    @pytest.mark.asyncio
    async def test_compress_empty_trace(
        self, trace_mgr: HiAgentTraceManager
    ):
        crystal = await trace_mgr.compress_subgoal("empty_goal")
        assert crystal["goal"] == "empty_goal"

    def test_flush_trace_direct(self, trace_mgr: HiAgentTraceManager):
        trace_mgr.record_step("a", "o")
        trace_mgr.flush_trace()
        assert trace_mgr.current_trace == []
