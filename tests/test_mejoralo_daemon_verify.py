"""Tests for MejoraloDaemon verify-after-heal loop.

Validates that the daemon re-scans after healing, records sessions
with real before/after scores, and escalates on stagnation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.mejoralo.daemon import STAGNATION_ESCALATION_THRESHOLD, MejoraloDaemon

# ── Minimal fakes ────────────────────────────────────────────────────


@dataclass
class FakeDimension:
    name: str = "complexity"
    score: int = 5
    weight: float = 1.0


@dataclass
class FakeScanResult:
    project: str = "test-project"
    stack: str = "python"
    score: int = 60
    dimensions: list = field(default_factory=lambda: [FakeDimension()])
    dead_code: bool = False
    total_files: int = 10
    total_loc: int = 500
    brutal: bool = False


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def daemon(tmp_path):
    """Create a MejoraloDaemon with all heavy dependencies mocked."""
    with (
        patch("cortex.mejoralo.daemon.get_engine") as mock_engine,
        patch("cortex.mejoralo.daemon.MejoraloEngine") as MockEngine,
        patch("cortex.mejoralo.daemon.CanaryMonitor") as MockCanary,
        patch("cortex.mejoralo.daemon.ContextFusion") as MockFusion,
    ):
        mock_engine.return_value = MagicMock()

        # Engine mock
        engine_inst = MockEngine.return_value
        engine_inst.scan = AsyncMock()
        engine_inst.heal = AsyncMock(return_value=True)
        engine_inst.relentless_heal = AsyncMock(return_value=True)
        engine_inst.record_session = MagicMock(return_value=1)

        # Canary mock
        canary_inst = MockCanary.return_value
        canary_inst.capture_baselines = MagicMock()
        canary_inst.verify = MagicMock(return_value=[])

        # Fusion mock
        fusion_inst = MockFusion.return_value
        fusion_inst.fuse_context = AsyncMock(return_value="fused context")

        d = MejoraloDaemon(
            project="test-project",
            base_path=tmp_path,
            target_score=80,
        )

        # Replace real MetricsRegistry with a mock for assertion tracking
        mock_metrics = MagicMock()
        d.metrics = mock_metrics

        # Store refs for test assertions
        d._mock_engine_inst = engine_inst
        d._mock_canary_inst = canary_inst
        d._mock_fusion_inst = fusion_inst

        yield d


# ── Tests ────────────────────────────────────────────────────────────


class TestVerifyAfterHeal:
    """Verify that _execute_cycle re-scans after heal and records real delta."""

    @pytest.mark.asyncio
    async def test_records_real_before_after_scores(self, daemon):
        """After healing, daemon should record session with actual scores."""
        scan_before = FakeScanResult(score=60)
        scan_after = FakeScanResult(score=72)

        daemon._mock_engine_inst.scan = AsyncMock(side_effect=[scan_before, scan_after])

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        # record_session should be called with real scores
        daemon._mock_engine_inst.record_session.assert_called_once_with(
            "test-project",
            60,
            72,
            actions=["autonomous_heal"],
        )

    @pytest.mark.asyncio
    async def test_sets_delta_gauge(self, daemon):
        """Daemon should set cortex_heal_delta gauge with the real delta."""
        scan_before = FakeScanResult(score=60)
        scan_after = FakeScanResult(score=75)

        daemon._mock_engine_inst.scan = AsyncMock(side_effect=[scan_before, scan_after])

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        # Check that set_gauge was called with delta = 15
        calls = daemon.metrics.set_gauge.call_args_list
        delta_calls = [c for c in calls if c[0][0] == "cortex_heal_delta"]
        assert len(delta_calls) == 1
        assert delta_calls[0][0][1] == 15  # 75 - 60

    @pytest.mark.asyncio
    async def test_no_heal_when_score_meets_target(self, daemon):
        """When score >= target, no healing should occur."""
        scan_good = FakeScanResult(score=85)  # target is 80
        daemon._mock_engine_inst.scan = AsyncMock(return_value=scan_good)

        await daemon._execute_cycle()

        daemon._mock_engine_inst.heal.assert_not_called()
        daemon._mock_engine_inst.record_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_stagnation_resets_on_improvement(self, daemon):
        """Stagnation counter should reset when delta > 0."""
        daemon._consecutive_stagnant = 2  # pre-set near threshold

        scan_before = FakeScanResult(score=60)
        scan_after = FakeScanResult(score=65)

        daemon._mock_engine_inst.scan = AsyncMock(side_effect=[scan_before, scan_after])

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        assert daemon._consecutive_stagnant == 0


class TestStagnationEscalation:
    """Verify that consecutive stagnation triggers relentless mode."""

    @pytest.mark.asyncio
    async def test_increments_stagnation_on_zero_delta(self, daemon):
        """When heal produces no improvement, stagnation counter should increase."""
        scan_result = FakeScanResult(score=60)
        daemon._mock_engine_inst.scan = AsyncMock(return_value=scan_result)

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        assert daemon._consecutive_stagnant == 1

    @pytest.mark.asyncio
    async def test_escalates_to_relentless_after_threshold(self, daemon):
        """After N stagnant cycles, daemon should switch to relentless_heal."""
        daemon._consecutive_stagnant = STAGNATION_ESCALATION_THRESHOLD

        scan_before = FakeScanResult(score=60)
        scan_after = FakeScanResult(score=62)

        daemon._mock_engine_inst.scan = AsyncMock(side_effect=[scan_before, scan_after])

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        # relentless_heal should have been called, NOT regular heal
        daemon._mock_engine_inst.relentless_heal.assert_called_once()
        daemon._mock_engine_inst.heal.assert_not_called()

        # Session should record "relentless_heal" action
        daemon._mock_engine_inst.record_session.assert_called_once()
        call_kwargs = daemon._mock_engine_inst.record_session.call_args
        assert (
            call_kwargs[1].get("actions") == ["relentless_heal"]
            or call_kwargs[0][3] == ["relentless_heal"]
            if len(call_kwargs[0]) > 3
            else "relentless_heal" in str(call_kwargs)
        )

    @pytest.mark.asyncio
    async def test_multiple_stagnant_cycles_accumulate(self, daemon):
        """Running N cycles with zero delta should accumulate stagnation."""
        scan_result = FakeScanResult(score=60)
        daemon._mock_engine_inst.scan = AsyncMock(return_value=scan_result)

        for i in range(STAGNATION_ESCALATION_THRESHOLD):
            with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
                with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                    await daemon._execute_cycle()

            assert daemon._consecutive_stagnant == i + 1


class TestScanCallPattern:
    """Ensure scan is called exactly twice per cycle (before + after heal)."""

    @pytest.mark.asyncio
    async def test_two_scans_per_cycle(self, daemon):
        """Daemon should scan once before and once after healing."""
        scan_before = FakeScanResult(score=60)
        scan_after = FakeScanResult(score=70)

        daemon._mock_engine_inst.scan = AsyncMock(side_effect=[scan_before, scan_after])

        with patch.object(daemon, "_ouroboros_analyze", new=AsyncMock(return_value="ctx")):
            with patch.object(daemon, "_ouroboros_absorb", new=AsyncMock()):
                await daemon._execute_cycle()

        assert daemon._mock_engine_inst.scan.call_count == 2
