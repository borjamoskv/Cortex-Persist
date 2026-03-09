"""Tests for NightShift Crystal Pipeline — Autonomous Knowledge Generation.

Tests the full DAG: KnowledgeRadar → PlannerNode → ExecutorNode →
ValidatorNode → PersisterNode, using mocked autodidact backend.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from cortex.swarm.knowledge_radar import (
    CrystalTarget,
    deduplicate_targets,
    merge_and_prioritize,
    scan_curated_queue,
)
from cortex.swarm.nightshift_pipeline import (
    ExecutorNode,
    HumanGateNode,
    NightShiftPipeline,
    PlannerNode,
    PersisterNode,
    ValidatorNode,
)
from cortex.swarm.nightshift_daemon import NightShiftCrystalDaemon


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_queue_file(tmp_path: Path) -> Path:
    """Create a temporary YAML queue file."""
    queue = tmp_path / "nightshift_queue.yaml"
    queue.write_text(
        """targets:
  - target: "https://example.com/docs"
    intent: "deep_learn"
    priority: 2
  - target: "how to build autonomous agents"
    intent: "search_gap"
    priority: 4
  - target: "https://example.com/api"
    intent: "quick_read"
    priority: 6
""",
        encoding="utf-8",
    )
    return queue


@pytest.fixture
def empty_queue_file(tmp_path: Path) -> Path:
    """Create an empty YAML queue file."""
    queue = tmp_path / "nightshift_queue.yaml"
    queue.write_text("targets: []\n", encoding="utf-8")
    return queue


@pytest.fixture
def sample_targets() -> list[CrystalTarget]:
    """Pre-built list of crystal targets."""
    return [
        CrystalTarget(target="https://example.com/a", intent="quick_read", priority=3),
        CrystalTarget(target="https://example.com/b", intent="deep_learn", priority=1),
        CrystalTarget(target="how react works", intent="search_gap", priority=5),
    ]


@pytest.fixture
def autodidact_success_mock():
    """Mock autodidact_pipeline to return success."""
    async def _mock(target: str, intent: str = "quick_read", force: bool = False) -> dict:
        return {"estado": "ASIMILADO", "memo_id": f"MEMO_{hash(target) % 10000:04X}"}

    return _mock


@pytest.fixture
def autodidact_failure_mock():
    """Mock autodidact_pipeline to return failure."""
    async def _mock(target: str, intent: str = "quick_read", force: bool = False) -> dict:
        return {"estado": "FALLO", "error": "Network timeout"}

    return _mock


# ── KnowledgeRadar Tests ──────────────────────────────────────────────────


class TestScanCuratedQueue:
    """Test YAML queue reading."""

    def test_reads_yaml_queue(self, sample_queue_file: Path) -> None:
        targets = scan_curated_queue(sample_queue_file)
        assert len(targets) == 3
        assert targets[0].target == "https://example.com/docs"
        assert targets[0].intent == "deep_learn"
        assert targets[0].priority == 2

    def test_empty_queue(self, empty_queue_file: Path) -> None:
        targets = scan_curated_queue(empty_queue_file)
        assert targets == []

    def test_missing_file(self, tmp_path: Path) -> None:
        targets = scan_curated_queue(tmp_path / "nonexistent.yaml")
        assert targets == []

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: valid: yaml: [", encoding="utf-8")
        targets = scan_curated_queue(bad_file)
        # Should return empty, not crash
        assert isinstance(targets, list)


class TestDeduplication:
    """Test target deduplication."""

    def test_removes_exact_duplicates(self) -> None:
        targets = [
            CrystalTarget(target="https://example.com", priority=1),
            CrystalTarget(target="https://example.com", priority=5),
        ]
        result = deduplicate_targets(targets)
        assert len(result) == 1
        # Keeps the first one
        assert result[0].priority == 1

    def test_case_insensitive(self) -> None:
        targets = [
            CrystalTarget(target="https://EXAMPLE.COM"),
            CrystalTarget(target="https://example.com"),
        ]
        result = deduplicate_targets(targets)
        assert len(result) == 1

    def test_preserves_unique(self) -> None:
        targets = [
            CrystalTarget(target="a"),
            CrystalTarget(target="b"),
            CrystalTarget(target="c"),
        ]
        result = deduplicate_targets(targets)
        assert len(result) == 3


class TestMergeAndPrioritize:
    """Test merge and cap logic."""

    def test_sorts_by_priority(self) -> None:
        low = [CrystalTarget(target="low", priority=10)]
        high = [CrystalTarget(target="high", priority=1)]
        result = merge_and_prioritize(low, high, max_n=5)
        assert result[0].target == "high"

    def test_caps_at_max_n(self) -> None:
        many = [CrystalTarget(target=f"t-{i}", priority=i) for i in range(20)]
        result = merge_and_prioritize(many, max_n=5)
        assert len(result) == 5

    def test_deduplicates_across_lists(self) -> None:
        a = [CrystalTarget(target="same", priority=1, source="curated")]
        b = [CrystalTarget(target="same", priority=5, source="ghost_gap")]
        result = merge_and_prioritize(a, b, max_n=10)
        assert len(result) == 1

    def test_empty_inputs(self) -> None:
        result = merge_and_prioritize([], [], max_n=5)
        assert result == []


# ── Pipeline Node Tests ───────────────────────────────────────────────────


class TestPlannerNode:
    """Test PlannerNode decomposition."""

    @pytest.mark.asyncio
    async def test_decomposes_crystal_targets(self, sample_targets: list[CrystalTarget]) -> None:
        planner = PlannerNode()
        state = {"targets": sample_targets}
        result = await planner.execute(state)
        assert len(result["plan"]) == 3
        assert result["next_node"] == "executor"

    @pytest.mark.asyncio
    async def test_handles_dict_targets(self) -> None:
        planner = PlannerNode()
        state = {"targets": [{"target": "https://example.com", "intent": "quick_read"}]}
        result = await planner.execute(state)
        assert len(result["plan"]) == 1
        assert result["plan"][0]["target"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_handles_string_targets(self) -> None:
        planner = PlannerNode()
        state = {"targets": ["https://example.com"]}
        result = await planner.execute(state)
        assert len(result["plan"]) == 1
        assert result["plan"][0]["intent"] == "quick_read"

    @pytest.mark.asyncio
    async def test_empty_targets(self) -> None:
        planner = PlannerNode()
        state = {"targets": []}
        result = await planner.execute(state)
        assert result["plan"] == []


class TestExecutorNode:
    """Test ExecutorNode with mocked autodidact."""

    @pytest.mark.asyncio
    async def test_calls_autodidact(self, autodidact_success_mock) -> None:
        executor = ExecutorNode()
        state = {
            "plan": [
                {"id": "crystal-1", "target": "https://example.com", "intent": "quick_read"},
            ],
        }
        with patch(
            "cortex.swarm.nightshift_pipeline.autodidact_pipeline",
            new=autodidact_success_mock,
            create=True,
        ):
            with patch(
                "cortex.skills.autodidact.actuator.autodidact_pipeline",
                new=autodidact_success_mock,
            ):
                result = await executor.execute(state)

        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True
        assert "MEMO" in result["results"][0]["output"]

    @pytest.mark.asyncio
    async def test_handles_failure(self, autodidact_failure_mock) -> None:
        executor = ExecutorNode()
        state = {
            "plan": [
                {"id": "crystal-1", "target": "https://example.com", "intent": "quick_read"},
            ],
        }
        with patch(
            "cortex.skills.autodidact.actuator.autodidact_pipeline",
            new=autodidact_failure_mock,
        ):
            result = await executor.execute(state)

        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is False

    @pytest.mark.asyncio
    async def test_handles_exception(self) -> None:
        executor = ExecutorNode()
        state = {
            "plan": [
                {"id": "crystal-1", "target": "https://example.com", "intent": "quick_read"},
            ],
        }

        async def _explode(**_kwargs: Any) -> dict:
            raise ConnectionError("DNS failure")

        with patch(
            "cortex.skills.autodidact.actuator.autodidact_pipeline",
            side_effect=ConnectionError("DNS failure"),
        ):
            result = await executor.execute(state)

        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is False
        assert "DNS failure" in result["results"][0].get("error", "")


class TestValidatorNode:
    """Test ValidatorNode confidence assignment."""

    @pytest.mark.asyncio
    async def test_all_success_is_c5(self) -> None:
        validator = ValidatorNode()
        state = {
            "results": [
                {"task_id": "1", "success": True, "output": "MEMO_1"},
                {"task_id": "2", "success": True, "output": "MEMO_2"},
            ],
        }
        result = await validator.execute(state)
        assert result["confidence"] == "C5"
        assert result["next_node"] == "persister"

    @pytest.mark.asyncio
    async def test_majority_success_is_c4(self) -> None:
        validator = ValidatorNode()
        state = {
            "results": [
                {"task_id": "1", "success": True, "output": "MEMO_1"},
                {"task_id": "2", "success": True, "output": "MEMO_2"},
                {"task_id": "3", "success": False, "output": ""},
            ],
        }
        result = await validator.execute(state)
        assert result["confidence"] == "C4"

    @pytest.mark.asyncio
    async def test_all_failure_goes_to_human_gate(self) -> None:
        validator = ValidatorNode()
        state = {
            "results": [
                {"task_id": "1", "success": False},
            ],
        }
        result = await validator.execute(state)
        assert result["confidence"] == "C2"
        assert result["next_node"] == "human_gate"


class TestPersisterNode:
    """Test PersisterNode metrics logging."""

    @pytest.mark.asyncio
    async def test_counts_crystals(self) -> None:
        persister = PersisterNode()
        state = {
            "results": [
                {"task_id": "1", "success": True, "output": "MEMO_A"},
                {"task_id": "2", "success": True, "output": "MEMO_B"},
                {"task_id": "3", "success": False, "output": ""},
            ],
            "confidence": "C4",
        }
        result = await persister.execute(state)
        assert result["crystals_count"] == 2
        assert "MEMO_A" in result["crystals_forged"]
        assert result["next_node"] == "__end__"


# ── Full Pipeline Tests ───────────────────────────────────────────────────


class TestNightShiftPipeline:
    """End-to-end pipeline tests with mocked autodidact."""

    @pytest.mark.asyncio
    async def test_end_to_end_success(self, sample_targets, autodidact_success_mock) -> None:
        pipeline = NightShiftPipeline()
        with patch(
            "cortex.skills.autodidact.actuator.autodidact_pipeline",
            new=autodidact_success_mock,
        ):
            result = await pipeline.run(targets=sample_targets)

        assert result["crystals_count"] == 3
        assert result["confidence"] == "C5"
        assert not result["is_paused"]

    @pytest.mark.asyncio
    async def test_empty_targets_no_crash(self) -> None:
        pipeline = NightShiftPipeline()
        result = await pipeline.run(targets=[])
        # Should complete without error, 0 crystals
        assert result.get("crystals_count", 0) == 0

    @pytest.mark.asyncio
    async def test_all_failures_pauses(self, sample_targets, autodidact_failure_mock) -> None:
        pipeline = NightShiftPipeline()
        with patch(
            "cortex.skills.autodidact.actuator.autodidact_pipeline",
            new=autodidact_failure_mock,
        ):
            result = await pipeline.run(targets=sample_targets)

        assert result["confidence"] == "C2"
        assert result["is_paused"] is True


# ── Daemon Tests ──────────────────────────────────────────────────────────


class TestNightShiftDaemon:
    """Test daemon lifecycle and limits."""

    @pytest.mark.asyncio
    async def test_respects_max_crystals(self, sample_queue_file, autodidact_success_mock) -> None:
        daemon = NightShiftCrystalDaemon(
            max_crystals=2,
            queue_path=sample_queue_file,
        )
        with patch(
            "cortex.skills.autodidact.actuator.autodidact_pipeline",
            new=autodidact_success_mock,
        ):
            report = await daemon.run_cycle()

        # Queue has 3 targets, but max_crystals=2
        assert report["targets_found"] <= 2

    @pytest.mark.asyncio
    async def test_empty_queue_no_crash(self, empty_queue_file) -> None:
        daemon = NightShiftCrystalDaemon(queue_path=empty_queue_file)
        report = await daemon.run_cycle()
        assert report["status"] == "idle"
        assert report["crystals"] == 0

    @pytest.mark.asyncio
    async def test_cycle_history(self, empty_queue_file) -> None:
        daemon = NightShiftCrystalDaemon(queue_path=empty_queue_file)
        await daemon.run_cycle()
        await daemon.run_cycle()
        assert len(daemon.history) == 2
        assert daemon.total_crystals == 0

    @pytest.mark.asyncio
    async def test_stop_daemon(self) -> None:
        """Daemon can be stopped cleanly."""
        daemon = NightShiftCrystalDaemon(cooldown_hours=0.001)
        daemon.stop()
        # Should return immediately since stop was already called
        await daemon.daemon_loop()
