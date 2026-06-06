# [C5-REAL] Exergy-Maximized
"""Tests for CortexSupervisor - Central Nervous System.

Validates:
    - Boot sequence (dependency order)
    - Task execution through full stack
    - Parameter sync L6 → L5
    - Preemptive actions from predictions
    - Health reporting
    - Graceful shutdown with persistence
    - Tuning restore on restart

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import pytest
import time
from pathlib import Path

from cortex.engine.supervisor import (
    CortexSupervisor,
    SupervisorConfig,
    AgentStatus,
)
from cortex.engine._autocurative_config import AutoCurativeConfig
from cortex.engine.self_optimizer import OptimizerConfig
from cortex.engine.predictive_healer import Prediction, PredictionType


# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def sv(tmp_path: Path) -> CortexSupervisor:
    config = SupervisorConfig(
        curative_config=AutoCurativeConfig(
            max_healing_attempts=3,
            cooldown_after_repair_s=0.01,
            breaker_failure_threshold=5,
        ),
        optimizer_config=OptimizerConfig(
            min_samples_for_tuning=5,
            confidence_threshold=0.5,
        ),
        persist_dir=str(tmp_path),
        heartbeat_interval_s=0.1,
    )
    return CortexSupervisor(config=config)


# ═══════════════════════════════════════════════════════════════════
# BOOT SEQUENCE
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_boot_sequence(sv: CortexSupervisor):
    """All agents boot successfully in order."""
    result = await sv.boot()

    assert all(s == AgentStatus.RUNNING for s in result.values())
    assert sv._boot_sequence_completed is True
    assert len(result) == 5


@pytest.mark.asyncio
async def test_boot_idempotent(sv: CortexSupervisor):
    """Booting twice doesn't crash."""
    await sv.boot()
    # Second boot through execute (auto-boots)
    result = await sv.execute(task=lambda: 42, subsystem="test")
    assert result == 42


# ═══════════════════════════════════════════════════════════════════
# TASK EXECUTION
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_execute_success(sv: CortexSupervisor):
    """Happy path execution through supervisor."""

    async def ok_task():
        return "done"

    result = await sv.execute(task=ok_task, subsystem="api")
    assert result == "done"
    assert sv._total_tasks_executed == 1

    # Telemetry recorded
    metrics = sv.tracker.get_metrics("api")
    assert metrics is not None
    assert metrics.total_successes == 1


@pytest.mark.asyncio
async def test_execute_sync_task(sv: CortexSupervisor):
    """Sync tasks are wrapped correctly."""
    result = await sv.execute(task=lambda: 99, subsystem="sync_test")
    assert result == 99


@pytest.mark.asyncio
async def test_execute_healing(sv: CortexSupervisor):
    """Task heals through L5 and telemetry feeds L6."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("timeout cascade")
        return "healed"

    result = await sv.execute(task=flaky, subsystem="flaky_api")
    assert result == "healed"
    assert sv.l5.health.total_errors_detected >= 1


@pytest.mark.asyncio
async def test_execute_failure_records_telemetry(sv: CortexSupervisor):
    """Failed task records error telemetry."""

    async def always_fail():
        raise RuntimeError("invariant: assertion broke")

    with pytest.raises(RuntimeError):
        await sv.execute(task=always_fail, subsystem="broken")

    metrics = sv.tracker.get_metrics("broken")
    assert metrics is not None
    assert metrics.total_errors >= 1
    assert sv._total_tasks_executed == 1


@pytest.mark.asyncio
async def test_execute_multiple_subsystems(sv: CortexSupervisor):
    """Tasks across different subsystems track independently."""
    await sv.execute(task=lambda: 1, subsystem="api")
    await sv.execute(task=lambda: 2, subsystem="db")
    await sv.execute(task=lambda: 3, subsystem="api")

    api = sv.tracker.get_metrics("api")
    db = sv.tracker.get_metrics("db")
    assert api is not None and api.total_executions == 2
    assert db is not None and db.total_executions == 1


# ═══════════════════════════════════════════════════════════════════
# PARAMETER SYNC
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_l6_to_l5_sync(sv: CortexSupervisor):
    """L6 tunings propagate to L5 config."""
    await sv.boot()

    sv.l6._tuned_params["api"] = {
        "timeout_ms": 15000.0,
        "cooldown_s": 3.0,
    }

    sv._sync_l6_to_l5()

    assert sv.l5.config.healing_timeout_s == 15.0
    assert sv.l5.config.cooldown_after_repair_s == 3.0


@pytest.mark.asyncio
async def test_l6_optimization_produces_tunings(sv: CortexSupervisor):
    """L6 optimizer cycle produces tuning decisions."""
    await sv.boot()

    # Feed enough telemetry
    for _ in range(20):
        sv.tracker.record_execution("worker", 10.0, success=False)

    event = await sv.l6.optimize()
    assert event.cycle_ms > 0


# ═══════════════════════════════════════════════════════════════════
# PREEMPTIVE ACTIONS
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_preemptive_batch_reduction(sv: CortexSupervisor):
    """Supervisor applies preemptive batch reduction."""
    await sv.boot()

    sv.l6._tuned_params["api"] = {"batch_size": 100}

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

    await sv._apply_preemptive_action(p)

    assert sv.l6.get_tuned_batch_size("api") < 100
    assert sv._total_preemptive_actions == 1


@pytest.mark.asyncio
async def test_preemptive_timeout_increase(sv: CortexSupervisor):
    """Supervisor applies preemptive timeout increase."""
    await sv.boot()

    sv.l6._tuned_params["db"] = {"timeout_ms": 5000.0}

    p = Prediction(
        type=PredictionType.LATENCY_DRIFT,
        subsystem="db",
        confidence=0.85,
        estimated_time_to_failure_s=45,
        current_value=4000,
        threshold=4500,
        trend_slope=50,
        recommended_action="PREEMPTIVE_TIMEOUT_INCREASE",
    )

    await sv._apply_preemptive_action(p)

    assert sv.l6.get_tuned_timeout("db") > 5000.0


@pytest.mark.asyncio
async def test_preemptive_breaker_warmup(sv: CortexSupervisor):
    """Supervisor pre-creates circuit breaker on pattern prediction."""
    await sv.boot()

    p = Prediction(
        type=PredictionType.RECURRING_PATTERN,
        subsystem="cron_job",
        confidence=0.8,
        estimated_time_to_failure_s=8,
        current_value=10,
        threshold=0,
        trend_slope=0.1,
        recommended_action="PREEMPTIVE_BREAKER_WARMUP",
    )

    await sv._apply_preemptive_action(p)

    # Breaker should exist now
    assert "cron_job" in sv.l5._breakers


# ═══════════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_persist_and_restore(sv: CortexSupervisor, tmp_path: Path):
    """Tunings persist on shutdown and restore on new boot."""
    await sv.boot()

    # Set tunings
    sv.l6._tuned_params["api"] = {"timeout_ms": 12000, "batch_size": 250}

    # Shutdown (persists)
    sv.shutdown()

    # New supervisor pointing to same dir
    sv2 = CortexSupervisor(config=SupervisorConfig(persist_dir=str(tmp_path)))
    await sv2.boot()

    # Tunings restored
    assert sv2.l6.get_tuned_timeout("api") == 12000
    assert sv2.l6.get_tuned_batch_size("api") == 250


# ═══════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_health_report(sv: CortexSupervisor):
    """Health report includes all layers."""
    await sv.boot()
    await sv.execute(task=lambda: 42, subsystem="test")

    h = sv.health()
    assert h["status"] == "healthy"
    assert h["agents_running"] == 5
    assert h["agents_total"] == 5
    assert h["tasks_executed"] == 1
    assert "l5_health" in h
    assert "l6_stats" in h
    assert "predictor_stats" in h


@pytest.mark.asyncio
async def test_status_string(sv: CortexSupervisor):
    """Quick status produces readable string."""
    await sv.boot()

    s = sv.status()
    assert "HEALTHY" in s
    assert "agents=5/5" in s


@pytest.mark.asyncio
async def test_health_before_boot(sv: CortexSupervisor):
    """Health report works before boot."""
    h = sv.health()
    assert h["agents_running"] == 0
    assert h["status"] == "critical"


# ═══════════════════════════════════════════════════════════════════
# SHUTDOWN
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_shutdown(sv: CortexSupervisor):
    """Graceful shutdown stops all agents."""
    await sv.boot()
    sv.shutdown()

    for info in sv._agents.values():
        assert info.status == AgentStatus.STOPPED


@pytest.mark.asyncio
async def test_shutdown_persists_state(sv: CortexSupervisor):
    """Shutdown persists tunings to disk."""
    await sv.boot()
    sv.l6._tuned_params["api"] = {"timeout_ms": 9000}

    sv.shutdown()

    # Verify on disk
    params = sv.store.load("api")
    assert params is not None
    assert params["timeout_ms"] == 9000


# ═══════════════════════════════════════════════════════════════════
# DIRECT ACCESS
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_direct_access_properties(sv: CortexSupervisor):
    """Escape hatch properties return correct instances."""
    assert sv.l5 is sv._l5
    assert sv.l6 is sv._l6
    assert sv.tracker is sv._tracker
    assert sv.predictor is sv._predictor
    assert sv.store is sv._store
