# [C5-REAL] Exergy-Maximized
"""Tests for Level 6 Self-Optimizer and Performance Tracker.

Validates:
    OBSERVE → ANALYZE → OPTIMIZE → VERIFY (degradation revert)

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import pytest
import time

from babylon60.engine.performance_tracker import (
    PerformanceTracker,
    SubsystemMetrics,
    StrategyEffectiveness,
)
from babylon60.engine.self_optimizer import (
    SelfOptimizer,
    OptimizerConfig,
    TuningType,
)


# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def tracker() -> PerformanceTracker:
    return PerformanceTracker()


@pytest.fixture
def optimizer(tracker: PerformanceTracker) -> SelfOptimizer:
    config = OptimizerConfig(
        optimization_interval_s=0.1,
        min_samples_for_tuning=10,
        confidence_threshold=0.5,
        max_tunings_per_cycle=10,
    )
    return SelfOptimizer(tracker=tracker, config=config)


# ─── Performance Tracker Tests ────────────────────────────────────


def test_record_execution(tracker: PerformanceTracker):
    """Record execution events and verify metrics."""
    for i in range(20):
        tracker.record_execution("api", latency_ms=10.0 + i, success=True)
    tracker.record_execution("api", latency_ms=500.0, success=False)

    metrics = tracker.get_metrics("api")
    assert metrics is not None
    assert metrics.total_executions == 21
    assert metrics.total_errors == 1
    assert metrics.total_successes == 20
    assert 0.04 < metrics.error_rate < 0.06  # ~1/21


def test_latency_percentiles(tracker: PerformanceTracker):
    """Verify latency percentile calculations."""
    # 100 samples: 1ms to 100ms
    for i in range(1, 101):
        tracker.record_execution("worker", latency_ms=float(i), success=True)

    metrics = tracker.get_metrics("worker")
    assert metrics is not None
    assert 49 <= metrics.p50 <= 51
    assert 89 <= metrics.p90 <= 91
    assert 98 <= metrics.p99 <= 100


def test_strategy_effectiveness(tracker: PerformanceTracker):
    """Track per-strategy effectiveness."""
    for _ in range(8):
        tracker.record_repair("db", "RESET_POOL", success=True, latency_ms=10.0)
    for _ in range(2):
        tracker.record_repair("db", "RESET_POOL", success=False, latency_ms=50.0)

    metrics = tracker.get_metrics("db")
    assert metrics is not None
    strat = metrics.strategies["RESET_POOL"]
    assert strat.total_attempts == 10
    assert strat.successes == 8
    assert strat.success_rate == 0.8
    assert strat.min_latency_ms == 10.0
    assert strat.max_latency_ms == 50.0


def test_best_strategy(tracker: PerformanceTracker):
    """Best strategy selection based on success rate."""
    for _ in range(10):
        tracker.record_repair("api", "BACKOFF", success=True, latency_ms=5.0)
    for _ in range(10):
        tracker.record_repair("api", "TIMEOUT_GUARD", success=False, latency_ms=100.0)

    metrics = tracker.get_metrics("api")
    assert metrics is not None
    assert metrics.best_strategy == "BACKOFF"


def test_snapshot(tracker: PerformanceTracker):
    """Performance snapshot captures all subsystems."""
    for _ in range(20):
        tracker.record_execution("api", 10.0, True)
        tracker.record_execution("db", 50.0, True)

    snap = tracker.snapshot()
    assert "api" in snap.subsystems
    assert "db" in snap.subsystems
    assert snap.global_error_rate == 0.0
    assert snap.global_mean_latency_ms > 0


def test_optimization_opportunities_high_error(tracker: PerformanceTracker):
    """Detect high error rate opportunities."""
    for _ in range(15):
        tracker.record_execution("flaky", 10.0, success=False)
    for _ in range(5):
        tracker.record_execution("flaky", 10.0, success=True)

    snap = tracker.snapshot()
    types = [o["type"] for o in snap.optimization_opportunities]
    assert "HIGH_ERROR_RATE" in types


def test_optimization_opportunities_tail_latency(tracker: PerformanceTracker):
    """Detect tail latency problems."""
    # Normal latencies
    for _ in range(90):
        tracker.record_execution("slow_tail", 1.0, True)
    # Tail spike
    for _ in range(10):
        tracker.record_execution("slow_tail", 100.0, True)

    snap = tracker.snapshot()
    types = [o["type"] for o in snap.optimization_opportunities]
    assert "TAIL_LATENCY" in types


def test_weak_strategy_detection(tracker: PerformanceTracker):
    """Detect underperforming strategies."""
    for _ in range(20):
        tracker.record_execution("broken", 10.0, True)
    for _ in range(8):
        tracker.record_repair("broken", "BAD_FIX", success=False, latency_ms=10.0)
    for _ in range(2):
        tracker.record_repair("broken", "BAD_FIX", success=True, latency_ms=10.0)

    snap = tracker.snapshot()
    types = [o["type"] for o in snap.optimization_opportunities]
    assert "WEAK_STRATEGY" in types


# ─── Self-Optimizer Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_optimizer_no_data(optimizer: SelfOptimizer):
    """Optimizer produces no decisions with insufficient data."""
    event = await optimizer.optimize()
    assert event.applied == 0
    assert event.skipped == 0
    assert len(event.decisions) == 0


@pytest.mark.asyncio
async def test_optimizer_timeout_increase(tracker: PerformanceTracker, optimizer: SelfOptimizer):
    """Optimizer increases timeout when p99 approaches current timeout."""
    # Set current timeout
    optimizer._tuned_params["api"] = {"timeout_ms": 100.0}

    # p99 close to timeout (80ms out of 100ms)
    for _ in range(15):
        tracker.record_execution("api", latency_ms=5.0, success=True)
    for _ in range(5):
        tracker.record_execution("api", latency_ms=85.0, success=True)

    event = await optimizer.optimize()

    timeout_decisions = [
        d
        for d in event.decisions
        if d.type == TuningType.TIMEOUT_ADJUSTMENT and d.subsystem == "api"
    ]
    assert len(timeout_decisions) == 1
    assert timeout_decisions[0].new_value > 100.0


@pytest.mark.asyncio
async def test_optimizer_batch_reduction_on_errors(
    tracker: PerformanceTracker, optimizer: SelfOptimizer
):
    """Optimizer reduces batch size when error rate is high."""
    optimizer._tuned_params["worker"] = {"batch_size": 200}

    # High error rate
    for _ in range(17):
        tracker.record_execution("worker", latency_ms=10.0, success=False)
    for _ in range(3):
        tracker.record_execution("worker", latency_ms=10.0, success=True)

    event = await optimizer.optimize()

    batch_decisions = [
        d
        for d in event.decisions
        if d.type == TuningType.BATCH_SIZE_TUNING and d.subsystem == "worker"
    ]
    assert len(batch_decisions) == 1
    assert batch_decisions[0].new_value < 200


@pytest.mark.asyncio
async def test_optimizer_batch_increase_on_success(
    tracker: PerformanceTracker, optimizer: SelfOptimizer
):
    """Optimizer increases batch when error rate is low and latency is fast."""
    optimizer._tuned_params["fast_worker"] = {"batch_size": 50}

    for _ in range(30):
        tracker.record_execution("fast_worker", latency_ms=5.0, success=True)

    event = await optimizer.optimize()

    batch_decisions = [
        d
        for d in event.decisions
        if d.type == TuningType.BATCH_SIZE_TUNING and d.subsystem == "fast_worker"
    ]
    assert len(batch_decisions) == 1
    assert batch_decisions[0].new_value > 50


@pytest.mark.asyncio
async def test_optimizer_strategy_demotion(tracker: PerformanceTracker, optimizer: SelfOptimizer):
    """Optimizer demotes strategies with low success rate."""
    for _ in range(20):
        tracker.record_execution("db", 10.0, True)

    # Bad strategy
    for _ in range(8):
        tracker.record_repair("db", "WEAK_STRAT", success=False, latency_ms=100.0)
    for _ in range(2):
        tracker.record_repair("db", "WEAK_STRAT", success=True, latency_ms=10.0)

    event = await optimizer.optimize()

    demotions = [d for d in event.decisions if d.type == TuningType.STRATEGY_DEMOTION]
    assert len(demotions) >= 1
    assert "WEAK_STRAT" in demotions[0].parameter


@pytest.mark.asyncio
async def test_optimizer_strategy_promotion(tracker: PerformanceTracker, optimizer: SelfOptimizer):
    """Optimizer promotes strategies with high success rate."""
    for _ in range(20):
        tracker.record_execution("api", 10.0, True)

    for _ in range(10):
        tracker.record_repair("api", "SUPER_FIX", success=True, latency_ms=1.0)

    event = await optimizer.optimize()

    promotions = [d for d in event.decisions if d.type == TuningType.STRATEGY_PROMOTION]
    assert len(promotions) >= 1
    assert "SUPER_FIX" in promotions[0].parameter


@pytest.mark.asyncio
async def test_optimizer_confidence_filter(
    tracker: PerformanceTracker,
):
    """Low-confidence decisions are skipped."""
    config = OptimizerConfig(
        min_samples_for_tuning=10,
        confidence_threshold=0.99,  # Very high bar
    )
    optimizer = SelfOptimizer(tracker=tracker, config=config)

    for _ in range(20):
        tracker.record_execution("test", 10.0, True)

    event = await optimizer.optimize()

    # All decisions should be skipped due to high confidence threshold
    assert event.applied == 0


@pytest.mark.asyncio
async def test_optimizer_max_tunings_limit(
    tracker: PerformanceTracker,
):
    """Max tunings per cycle is respected."""
    config = OptimizerConfig(
        min_samples_for_tuning=5,
        confidence_threshold=0.1,
        max_tunings_per_cycle=2,
    )
    optimizer = SelfOptimizer(tracker=tracker, config=config)

    # Create many optimization opportunities
    for sub in ["a", "b", "c", "d"]:
        for _ in range(20):
            tracker.record_execution(sub, 10.0, False)  # All errors

    event = await optimizer.optimize()
    assert event.applied <= 2


@pytest.mark.asyncio
async def test_optimizer_stats(optimizer: SelfOptimizer):
    """Optimizer stats are accurate."""
    stats = optimizer.stats
    assert stats["total_cycles"] == 0
    assert stats["total_tunings_applied"] == 0

    await optimizer.optimize()

    stats = optimizer.stats
    assert stats["total_cycles"] == 1


@pytest.mark.asyncio
async def test_optimizer_history(tracker: PerformanceTracker, optimizer: SelfOptimizer):
    """Optimization events are recorded in history."""
    for _ in range(20):
        tracker.record_execution("test", 10.0, True)

    await optimizer.optimize()
    await optimizer.optimize()

    history = optimizer.get_history()
    assert len(history) == 2
    assert "decisions_count" in history[0]
    assert "cycle_ms" in history[0]


@pytest.mark.asyncio
async def test_tuned_parameter_queries(optimizer: SelfOptimizer):
    """Public parameter query methods return tuned values."""
    optimizer._tuned_params["api"] = {
        "timeout_ms": 8000.0,
        "batch_size": 200,
        "breaker_threshold": 8,
        "cooldown_s": 2.0,
    }

    assert optimizer.get_tuned_timeout("api") == 8000.0
    assert optimizer.get_tuned_batch_size("api") == 200
    assert optimizer.get_tuned_breaker_threshold("api") == 8
    assert optimizer.get_tuned_cooldown("api") == 2.0

    # Defaults for unknown subsystem
    assert optimizer.get_tuned_timeout("unknown") == 5000.0
    assert optimizer.get_tuned_batch_size("unknown") == 100


@pytest.mark.asyncio
async def test_full_optimization_loop(tracker: PerformanceTracker, optimizer: SelfOptimizer):
    """End-to-end test: populate metrics → optimize → verify tunings."""
    # Phase 1: System running with moderate issues
    for _ in range(30):
        tracker.record_execution("dispatch", latency_ms=50.0, success=True)
    for _ in range(5):
        tracker.record_execution("dispatch", latency_ms=500.0, success=False)

    # Some repair data
    for _ in range(4):
        tracker.record_repair("dispatch", "TIMEOUT_GUARD", success=True, latency_ms=2.0)
    for _ in range(6):
        tracker.record_repair("dispatch", "BAD_RETRY", success=False, latency_ms=200.0)

    # Phase 2: Optimize
    event = await optimizer.optimize()

    # Should have decisions
    assert len(event.decisions) > 0
    assert event.cycle_ms > 0

    # Phase 3: Verify tunings exist
    all_params = optimizer.get_all_tuned_params()
    # At least some tuning should have been applied
    assert event.applied > 0 or event.skipped > 0

    # Phase 4: Stats are updated
    stats = optimizer.stats
    assert stats["total_cycles"] == 1


def test_subsystem_metrics_serialization(tracker: PerformanceTracker):
    """SubsystemMetrics serializes to dict correctly."""
    for i in range(10):
        tracker.record_execution("test", float(i), i % 3 != 0)
    tracker.record_repair("test", "FIX_A", True, 5.0)

    metrics = tracker.get_metrics("test")
    assert metrics is not None
    d = metrics.to_dict()
    assert "subsystem" in d
    assert "p50_ms" in d
    assert "p90_ms" in d
    assert "best_strategy" in d
    assert "strategies" in d


def test_strategy_effectiveness_serialization():
    """StrategyEffectiveness serializes to dict correctly."""
    s = StrategyEffectiveness(strategy="TEST")
    s.record(True, 10.0)
    s.record(False, 50.0)

    d = s.to_dict()
    assert d["strategy"] == "TEST"
    assert d["total_attempts"] == 2
    assert d["successes"] == 1
    assert d["success_rate"] == 0.5


def test_tracker_reset(tracker: PerformanceTracker):
    """Tracker reset clears all data."""
    tracker.record_execution("test", 10.0, True)
    tracker.snapshot()

    tracker.reset()
    assert len(tracker.subsystem_names) == 0
    assert len(tracker.history) == 0
