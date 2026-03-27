"""Tests for Memory OS modules (RFC-CORTEX-MEMORY-OS).

Covers: Mem0Pipeline, MemoryOS, HiAgentTraceManager.
Aligned with refactored API (v8 / Industrial Noir 2026).
"""

from __future__ import annotations

import pytest

from cortex.compaction.mem0_pipeline import ExergyScore, Mem0Pipeline
from cortex.extensions.context.hiagent import HiAgentTraceManager
from cortex.extensions.policy.memory_os import MemoryOS

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
    async def test_extract_crystallized_keyword(self, pipeline: Mem0Pipeline):
        """Extract returns facts when 'crystallized' keyword is present."""
        result = await pipeline.extract("This is a crystallized observation")
        assert len(result) == 1
        assert result[0]["entity"] == "subgoal"

    @pytest.mark.asyncio
    async def test_consolidate_deduplicates(self, pipeline: Mem0Pipeline):
        facts = [
            {"entity": "a", "fact": "x"},
            {"entity": "a", "fact": "x"},  # duplicate
            {"entity": "b", "fact": "y"},
        ]
        result = await pipeline.consolidate(facts)
        assert len(result) == 2  # deduplicated

    @pytest.mark.asyncio
    async def test_evaluate_exergy_default(self, pipeline: Mem0Pipeline):
        score = await pipeline.evaluate_exergy({"content": "test"})
        assert isinstance(score, ExergyScore)
        assert score.score >= 0.0

    @pytest.mark.asyncio
    async def test_evaluate_exergy_short_text(self, pipeline: Mem0Pipeline):
        """Short text should have low signal gain."""
        score = await pipeline.evaluate_exergy({"c": "x"})
        assert score.score < 0.5

    @pytest.mark.asyncio
    async def test_evaluate_exergy_long_text(self, pipeline: Mem0Pipeline):
        """Longer text should have higher signal gain."""
        score = await pipeline.evaluate_exergy({"content": "a" * 100})
        assert score.score >= 0.5

    def test_exergy_dataclass(self):
        s = ExergyScore(score=0.75, justification="High utility")
        assert s.score == 0.75
        assert s.justification == "High utility"


# ─── MemoryOS ────────────────────────────────────────────────────────


class TestMemoryOS:
    """Memory OS hypervisor tests (refactored: persist + gc only)."""

    @pytest.fixture
    def memory_os(self) -> MemoryOS:
        return MemoryOS()

    @pytest.mark.asyncio
    async def test_persist_no_facts(self, memory_os: MemoryOS):
        """Empty context produces zero stored facts."""
        result = await memory_os.persist_episodic_to_semantic("nothing here")
        assert result == 0

    @pytest.mark.asyncio
    async def test_persist_with_crystallized(self, memory_os: MemoryOS):
        """Context with 'crystallized' should extract and attempt persistence."""
        # This may store 0 or more depending on exergy threshold and ledger state.
        result = await memory_os.persist_episodic_to_semantic(
            "This is a crystallized observation with detailed data."
        )
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_gc_without_engine(self, memory_os: MemoryOS):
        """GC without engine should complete without error."""
        await memory_os.gc()  # Should not raise


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
    async def test_compress_subgoal_returns_crystal(self, trace_mgr: HiAgentTraceManager):
        trace_mgr.record_step("a1", "o1")
        trace_mgr.record_step("a2", "o2")
        crystal = await trace_mgr.compress_subgoal("test_goal")
        assert crystal["goal"] == "test_goal"
        assert "crystal" in crystal

    @pytest.mark.asyncio
    async def test_compress_flushes_trace(self, trace_mgr: HiAgentTraceManager):
        """Amnesia Local: trace must be empty after compression."""
        trace_mgr.record_step("a1", "o1")
        await trace_mgr.compress_subgoal("test_goal")
        assert len(trace_mgr.current_trace) == 0

    @pytest.mark.asyncio
    async def test_compress_empty_trace(self, trace_mgr: HiAgentTraceManager):
        crystal = await trace_mgr.compress_subgoal("empty_goal")
        assert crystal["goal"] == "empty_goal"

    def test_flush_trace_direct(self, trace_mgr: HiAgentTraceManager):
        trace_mgr.record_step("a", "o")
        trace_mgr.flush_trace()
        assert trace_mgr.current_trace == []
