# [C5-REAL] Exergy-Maximized
"""Tests for Predictive Healer + Tuning Persistence + HealingStack v2.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import json
import pytest
import tempfile
import time
from pathlib import Path

from babylon60.engine.forensic.predictive_healer import (
    PredictiveHealer,
    Prediction,
    PredictionType,
    _TrendWindow,
)
from babylon60.engine.core.tuning_store import TuningStore
from babylon60.engine.core.performance_tracker import PerformanceTracker
from babylon60.engine.evo.healing_stack import HealingStack, HealingStackConfig
from babylon60.engine.evo._autocurative_config import AutoCurativeConfig
from babylon60.engine.self_optimizer import OptimizerConfig


# ═══════════════════════════════════════════════════════════════════
# TREND ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════════════


def test_trend_linear_regression_flat():
    """Flat data → slope ≈ 0."""
    tw = _TrendWindow(max_size=50)
    for i in range(20):
        tw.push(5.0, timestamp=float(i))
    slope, intercept, r_sq = tw.linear_regression()
    assert abs(slope) < 0.001


def test_trend_linear_regression_rising():
    """Linearly rising data → positive slope."""
    tw = _TrendWindow(max_size=50)
    for i in range(20):
        tw.push(float(i) * 0.1, timestamp=float(i))
    slope, intercept, r_sq = tw.linear_regression()
    assert slope > 0.09
    assert r_sq > 0.99


def test_trend_extrapolate_to_threshold():
    """Extrapolate time to reach threshold."""
    tw = _TrendWindow(max_size=50)
    # Rate rising from 0.0 to 0.1 over 10 seconds
    for i in range(11):
        tw.push(float(i) * 0.01, timestamp=float(i))

    # Threshold = 0.2 → should take another ~10 seconds
    ttf = tw.extrapolate_to_threshold(0.2)
    assert ttf is not None
    assert 8.0 < ttf < 12.0


def test_trend_extrapolate_flat_returns_none():
    """Flat trend can't extrapolate."""
    tw = _TrendWindow(max_size=50)
    for i in range(10):
        tw.push(0.05, timestamp=float(i))
    assert tw.extrapolate_to_threshold(0.2) is None


# ═══════════════════════════════════════════════════════════════════
# PREDICTIVE HEALER TESTS
# ═══════════════════════════════════════════════════════════════════


def test_predict_error_rate_rising():
    """Detect rising error rate trend."""
    healer = PredictiveHealer(min_samples=5, error_rate_threshold=0.2)

    for i in range(10):
        healer.record_error_rate("api", 0.02 * i, timestamp=float(i))

    predictions = healer.predict_all()
    err_preds = [p for p in predictions if p.type == PredictionType.ERROR_RATE_RISING]
    assert len(err_preds) >= 1
    assert err_preds[0].subsystem == "api"
    assert err_preds[0].trend_slope > 0


def test_predict_latency_drift():
    """Detect latency creeping toward timeout."""
    healer = PredictiveHealer(min_samples=5)

    for i in range(10):
        healer.record_latency("db", 100.0 + i * 50, timestamp=float(i))

    predictions = healer.predict_all()
    lat_preds = [p for p in predictions if p.type == PredictionType.LATENCY_DRIFT]
    assert len(lat_preds) >= 1
    assert lat_preds[0].trend_slope > 0


def test_predict_recurring_pattern():
    """Detect periodic error pattern."""
    healer = PredictiveHealer(min_samples=3)

    base = time.monotonic()
    # Errors every 10 seconds (regular interval)
    for i in range(5):
        healer.record_error_event("cron_job", timestamp=base + i * 10)

    predictions = healer.predict_all()
    recurring = [p for p in predictions if p.type == PredictionType.RECURRING_PATTERN]
    assert len(recurring) >= 1
    assert recurring[0].confidence > 0.5


def test_predict_cortisol_momentum():
    """Detect cortisol trending toward alarm threshold."""
    healer = PredictiveHealer(min_samples=5, cortisol_threshold=0.7)

    for i in range(10):
        healer.record_cortisol(0.1 + i * 0.05, timestamp=float(i))

    predictions = healer.predict_all()
    cortisol_preds = [p for p in predictions if p.type == PredictionType.CORTISOL_MOMENTUM]
    assert len(cortisol_preds) >= 1


def test_predict_no_data():
    """No predictions with insufficient data."""
    healer = PredictiveHealer(min_samples=10)
    predictions = healer.predict_all()
    assert len(predictions) == 0


def test_predict_stable_system():
    """Stable system → no predictions."""
    healer = PredictiveHealer(min_samples=5, error_rate_threshold=0.2)

    for i in range(20):
        healer.record_error_rate("stable", 0.01, timestamp=float(i))
        healer.record_latency("stable", 10.0, timestamp=float(i))

    predictions = healer.predict_all()
    assert len(predictions) == 0


def test_prediction_is_critical():
    """Critical flag works correctly."""
    p = Prediction(
        type=PredictionType.ERROR_RATE_RISING,
        subsystem="test",
        confidence=0.9,
        estimated_time_to_failure_s=30,
        current_value=0.15,
        threshold=0.2,
        trend_slope=0.01,
        recommended_action="REDUCE_BATCH",
    )
    assert p.is_critical is True

    p2 = Prediction(
        type=PredictionType.ERROR_RATE_RISING,
        subsystem="test",
        confidence=0.3,
        estimated_time_to_failure_s=30,
        current_value=0.15,
        threshold=0.2,
        trend_slope=0.01,
        recommended_action="REDUCE_BATCH",
    )
    assert p2.is_critical is False


def test_predictor_stats():
    """Predictor stats are accurate."""
    healer = PredictiveHealer(min_samples=3)
    for i in range(5):
        healer.record_error_rate("api", 0.05 * i, timestamp=float(i))

    healer.predict_all()
    stats = healer.stats
    assert "total_predictions" in stats
    assert "tracked_subsystems" in stats
    assert "api" in stats["tracked_subsystems"]


# ═══════════════════════════════════════════════════════════════════
# TUNING STORE TESTS
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def store(tmp_path: Path) -> TuningStore:
    return TuningStore(base_dir=tmp_path)


def test_store_save_and_load(store: TuningStore):
    """Save and load tunings for a subsystem."""
    store.save("api", {"timeout_ms": 8000, "batch_size": 200})
    params = store.load("api")

    assert params is not None
    assert params["timeout_ms"] == 8000
    assert params["batch_size"] == 200


def test_store_load_nonexistent(store: TuningStore):
    """Loading nonexistent subsystem returns None."""
    assert store.load("nonexistent") is None


def test_store_load_all(store: TuningStore):
    """Load all subsystem tunings."""
    store.save("api", {"timeout_ms": 5000})
    store.save("db", {"batch_size": 50})

    all_params = store.load_all()
    assert "api" in all_params
    assert "db" in all_params
    assert all_params["api"]["timeout_ms"] == 5000


def test_store_delete(store: TuningStore):
    """Delete persisted tunings."""
    store.save("temp", {"x": 1})
    assert store.load("temp") is not None

    assert store.delete("temp") is True
    assert store.load("temp") is None
    assert store.delete("temp") is False


def test_store_snapshot(store: TuningStore):
    """Snapshot saves all params + stats."""
    all_params = {
        "api": {"timeout_ms": 8000},
        "db": {"batch_size": 100},
    }
    stats = {"total_cycles": 5}

    store.snapshot(all_params, stats)

    snap = store.load_snapshot()
    assert snap is not None
    assert "api" in snap["params"]
    assert snap["stats"]["total_cycles"] == 5


def test_store_subsystems_list(store: TuningStore):
    """List persisted subsystems."""
    store.save("alpha", {"x": 1})
    store.save("beta", {"y": 2})

    subs = store.subsystems
    assert "alpha" in subs
    assert "beta" in subs


def test_store_overwrites(store: TuningStore):
    """Saving twice overwrites previous value."""
    store.save("api", {"timeout_ms": 5000})
    store.save("api", {"timeout_ms": 10000})

    params = store.load("api")
    assert params is not None
    assert params["timeout_ms"] == 10000


# ═══════════════════════════════════════════════════════════════════
# HEALING STACK V2 TESTS
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def stack_v2(tmp_path: Path) -> HealingStack:
    config = HealingStackConfig(
        curative_config=AutoCurativeConfig(
            max_healing_attempts=3,
            cooldown_after_repair_s=0.01,
            breaker_failure_threshold=5,
        ),
        optimizer_config=OptimizerConfig(
            min_samples_for_tuning=5,
            confidence_threshold=0.5,
        ),
        sync_interval_s=0.1,
        prediction_interval_s=0.1,
        persist_interval_s=0.1,
        persist_dir=tmp_path,
        enable_prediction=True,
        enable_persistence=True,
    )
    return HealingStack(config=config)


@pytest.mark.asyncio
async def test_stack_v2_execute_success(stack_v2: HealingStack):
    """Happy path through v2 stack."""

    async def ok():
        return "done"

    result = await stack_v2.execute(task=ok, subsystem="test")
    assert result == "done"

    metrics = stack_v2._tracker.get_metrics("test")
    assert metrics is not None
    assert metrics.total_successes == 1


@pytest.mark.asyncio
async def test_stack_v2_healing_with_telemetry(stack_v2: HealingStack):
    """Healing event feeds telemetry to L6."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("timeout")
        return "ok"

    result = await stack_v2.execute(task=flaky, subsystem="api")
    assert result == "ok"

    # L5 detected the error
    assert stack_v2._agent.health.total_errors_detected >= 1

    # L6 has telemetry
    metrics = stack_v2._tracker.get_metrics("api")
    assert metrics is not None


@pytest.mark.asyncio
async def test_stack_v2_full_sync(stack_v2: HealingStack):
    """All parameters sync from L6 to L5."""
    stack_v2._optimizer._tuned_params["api"] = {
        "timeout_ms": 10000.0,
        "batch_size": 200,
        "cooldown_s": 2.0,
        "breaker_threshold": 8,
    }

    stack_v2._sync_parameters_sync()

    # Timeout should be synced to agent config
    assert stack_v2._agent.config.healing_timeout_s == 10.0
    assert stack_v2._agent.config.cooldown_after_repair_s == 2.0


@pytest.mark.asyncio
async def test_stack_v2_persistence(stack_v2: HealingStack):
    """Tunings persist to disk and survive reload."""
    stack_v2._optimizer._tuned_params["api"] = {"timeout_ms": 9000}
    stack_v2.persist_now()

    # Verify file exists
    assert stack_v2._store is not None
    params = stack_v2._store.load("api")
    assert params is not None
    assert params["timeout_ms"] == 9000


@pytest.mark.asyncio
async def test_stack_v2_restore_on_init(tmp_path: Path):
    """Tunings are restored from disk on initialization."""
    # First: save tunings
    store = TuningStore(base_dir=tmp_path)
    store.save("api", {"timeout_ms": 12000, "batch_size": 500})

    # Second: create new stack pointing to same dir
    config = HealingStackConfig(
        persist_dir=tmp_path,
        enable_persistence=True,
    )
    stack = HealingStack(config=config)

    # Verify tunings were restored
    assert stack.get_timeout("api") == 12000
    assert stack.get_batch_size("api") == 500


@pytest.mark.asyncio
async def test_stack_v2_prediction(stack_v2: HealingStack):
    """Predictions work through the stack."""
    # Feed rising error rates
    for i in range(10):
        stack_v2._predictor.record_error_rate("db", 0.02 * i, timestamp=float(i))

    predictions = stack_v2.predict()
    assert len(predictions) >= 1


@pytest.mark.asyncio
async def test_stack_v2_health_report(stack_v2: HealingStack):
    """Health report includes all layers."""
    await stack_v2.execute(task=lambda: 42, subsystem="test")

    health = stack_v2.health
    assert "agent" in health
    assert "optimizer" in health
    assert "predictor" in health
    assert "persisted_subsystems" in health
    assert "uptime_s" in health


@pytest.mark.asyncio
async def test_stack_v2_preemptive_action(stack_v2: HealingStack):
    """Preemptive action is applied for high-confidence predictions."""
    p = Prediction(
        type=PredictionType.ERROR_RATE_RISING,
        subsystem="api",
        confidence=0.9,
        estimated_time_to_failure_s=30,
        current_value=0.15,
        threshold=0.2,
        trend_slope=0.01,
        recommended_action="PREEMPTIVE_BATCH_REDUCTION",
    )

    # Set initial batch size
    stack_v2._optimizer._tuned_params["api"] = {"batch_size": 100}

    await stack_v2._apply_preemptive_action(p)

    # Batch should have been reduced
    new_batch = stack_v2.get_batch_size("api")
    assert new_batch < 100
    assert stack_v2._predictor._total_preventions == 1


@pytest.mark.asyncio
async def test_stack_v2_cooldown_query(stack_v2: HealingStack):
    """Cooldown parameter is queryable."""
    stack_v2._optimizer._tuned_params["api"] = {"cooldown_s": 3.0}
    assert stack_v2.get_cooldown("api") == 3.0
    assert stack_v2.get_cooldown("unknown") == 5.0  # default
