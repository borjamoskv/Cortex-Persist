"""Tests for the Unified Healing Stack (L5 + L6).

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import pytest

from cortex.engine.healing_stack import HealingStack, HealingStackConfig
from cortex.engine._autocurative_config import AutoCurativeConfig
from cortex.engine.self_optimizer import OptimizerConfig


@pytest.fixture
def stack() -> HealingStack:
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
    )
    return HealingStack(config=config)


@pytest.mark.asyncio
async def test_stack_execute_success(stack: HealingStack):
    """Happy path through unified stack."""

    async def ok_task():
        return "done"

    result = await stack.execute(task=ok_task, subsystem="test")
    assert result == "done"

    # Telemetry should be recorded
    metrics = stack._tracker.get_metrics("test")
    assert metrics is not None
    assert metrics.total_executions == 1
    assert metrics.total_successes == 1


@pytest.mark.asyncio
async def test_stack_execute_with_healing(stack: HealingStack):
    """Task heals through L5 and telemetry feeds L6."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("timeout")
        return "healed"

    result = await stack.execute(task=flaky, subsystem="api")
    assert result == "healed"

    # L5 recorded the healing
    agent_health = stack._agent.health
    assert agent_health.total_errors_detected >= 1

    # L6 has telemetry
    metrics = stack._tracker.get_metrics("api")
    assert metrics is not None


@pytest.mark.asyncio
async def test_stack_execute_failure_records_telemetry(stack: HealingStack):
    """Failed task records failure telemetry for L6."""

    async def always_fail():
        raise RuntimeError("invariant: assertion broke")

    with pytest.raises(RuntimeError):
        await stack.execute(task=always_fail, subsystem="core")

    metrics = stack._tracker.get_metrics("core")
    assert metrics is not None
    assert metrics.total_errors >= 1


@pytest.mark.asyncio
async def test_stack_optimization_cycle(stack: HealingStack):
    """L6 optimizer runs and produces tuning decisions."""
    # Feed enough telemetry
    for _ in range(10):
        try:
            await stack.execute(
                task=lambda: "ok",
                subsystem="worker",
            )
        except Exception:
            pass

    # Run optimizer
    event = await stack._optimizer.optimize()
    assert event is not None
    assert event.cycle_ms > 0


@pytest.mark.asyncio
async def test_stack_health_report(stack: HealingStack):
    """Combined health report includes L5, L6, and telemetry."""
    await stack.execute(task=lambda: 42, subsystem="test")

    health = stack.health
    assert "agent" in health
    assert "optimizer" in health
    assert "uptime_s" in health
    assert health["agent"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_stack_parameter_queries(stack: HealingStack):
    """Optimized parameters are queryable."""
    # Before any optimization, returns defaults
    assert stack.get_timeout("api") == 5000.0
    assert stack.get_batch_size("api") == 100

    # After manual tuning
    stack._optimizer._tuned_params["api"] = {
        "timeout_ms": 8000.0,
        "batch_size": 200,
    }
    assert stack.get_timeout("api") == 8000.0
    assert stack.get_batch_size("api") == 200
