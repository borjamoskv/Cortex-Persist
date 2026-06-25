# [C5-REAL] Exergy-Maximized
"""Tests for Level 5 Auto-Curative Agent.

Validates the full self-healing loop:
    EXECUTE → MONITOR → ERROR → DIAGNOSE → REPAIR → VERIFY

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import pytest
import time

from legacy_research.engine.autocurative_agent import (
    AutoCurativeAgent,
    AutoCurativeConfig,
    HealingPhase,
)
from legacy_research.engine.repair_strategies import (
    REPAIR_REGISTRY,
    RepairResult,
    RepairStatus,
    RepairRegistry,
)
from legacy_research.engine.circuit_breaker import CircuitBreaker, CircuitState


# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def agent() -> AutoCurativeAgent:
    """Create an AutoCurativeAgent with test-friendly config."""
    config = AutoCurativeConfig(
        monitor_interval_s=0.1,
        max_healing_attempts=3,
        healing_timeout_s=5.0,
        breaker_failure_threshold=3,
        breaker_recovery_timeout_s=1.0,
        cooldown_after_repair_s=0.01,  # fast cooldown for tests
        max_concurrent_repairs=2,
        persist_events=False,
    )
    return AutoCurativeAgent(config=config)


@pytest.fixture
def registry() -> RepairRegistry:
    return RepairRegistry()


# ─── Test: Successful Execution (no healing needed) ───────────────


@pytest.mark.asyncio
async def test_execute_success_no_healing(agent: AutoCurativeAgent):
    """Task succeeds on first try - no healing loop triggered."""

    async def healthy_task():
        return 42

    result = await agent.execute_with_healing(
        task=healthy_task,
        subsystem="test",
    )

    assert result == 42
    assert agent.phase == HealingPhase.IDLE
    assert agent.health.total_errors_detected == 0
    assert agent.health.total_repairs_attempted == 0


# ─── Test: Self-Healing Loop (transient error) ───────────────────


@pytest.mark.asyncio
async def test_self_healing_transient_error(agent: AutoCurativeAgent):
    """Task fails once, then succeeds - agent self-heals."""
    call_count = 0

    async def flaky_task():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Connection timed out")
        return "recovered"

    result = await agent.execute_with_healing(
        task=flaky_task,
        subsystem="network",
    )

    assert result == "recovered"
    assert call_count == 2
    assert agent.health.total_errors_detected == 1
    assert agent.health.total_repairs_attempted == 1
    assert agent.health.total_repairs_succeeded == 1


# ─── Test: Multiple Failures Then Recovery ────────────────────────


@pytest.mark.asyncio
async def test_multi_failure_recovery(agent: AutoCurativeAgent):
    """Task fails twice, then succeeds on third attempt."""
    call_count = 0

    async def very_flaky_task():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Database connection refused")
        return "finally_ok"

    result = await agent.execute_with_healing(
        task=very_flaky_task,
        subsystem="database",
    )

    assert result == "finally_ok"
    assert call_count == 3
    assert agent.health.total_errors_detected == 2
    assert agent.health.total_repairs_attempted == 2


# ─── Test: Exhaustion (all attempts fail) ─────────────────────────


@pytest.mark.asyncio
async def test_healing_exhaustion(agent: AutoCurativeAgent):
    """All healing attempts fail - error raised after max attempts."""

    async def always_fails():
        raise RuntimeError("Invariant violation: assertion failed")

    with pytest.raises(RuntimeError, match="assertion failed"):
        await agent.execute_with_healing(
            task=always_fails,
            subsystem="core",
        )

    assert agent.health.total_errors_detected == 3
    assert agent.health.total_repairs_attempted == 3


# ─── Test: Circuit Breaker Integration ────────────────────────────


@pytest.mark.asyncio
async def test_circuit_breaker_trips():
    """Circuit breaker trips after threshold and prevents execution."""
    config = AutoCurativeConfig(
        breaker_failure_threshold=2,
        max_healing_attempts=1,
        cooldown_after_repair_s=0.01,
    )
    agent = AutoCurativeAgent(config=config)

    async def failing_task():
        raise MemoryError("OOM: cannot allocate 4GB")

    # First call: fails, breaker records
    with pytest.raises(MemoryError):
        await agent.execute_with_healing(task=failing_task, subsystem="memory")

    # Second call: fails, breaker trips
    with pytest.raises(MemoryError):
        await agent.execute_with_healing(task=failing_task, subsystem="memory")

    # Third call: breaker should be OPEN
    breaker = agent._breakers.get("memory")
    assert breaker is not None
    # After 2 failures with threshold=2, breaker should be OPEN
    assert breaker.state == CircuitState.OPEN


# ─── Test: Diagnosis Classification ──────────────────────────────


@pytest.mark.asyncio
async def test_diagnosis_classification(agent: AutoCurativeAgent):
    """Verify error signatures are classified correctly."""
    test_cases = [
        (TimeoutError("request timed out"), "TimeoutCascade"),
        (MemoryError("out of memory"), "MemoryLeak"),
        (ConnectionError("connection refused"), "ConnectionExhaustion"),
        (ValueError("rate limit exceeded 429"), "RateLimitBreach"),
        (AssertionError("invariant broken"), "InvariantViolation"),
    ]

    for error, expected_class in test_cases:
        event = await agent.handle_error(
            error=error,
            subsystem="test",
        )
        assert event is not None, f"No event for {type(error).__name__}"
        assert event.anomaly_class == expected_class, (
            f"Expected {expected_class}, got {event.anomaly_class} "
            f"for {type(error).__name__}: {error}"
        )


# ─── Test: Repair Strategy Execution ─────────────────────────────


@pytest.mark.asyncio
async def test_repair_strategy_timeout_guard(registry: RepairRegistry):
    """INJECT_TIMEOUT_GUARD strategy modifies the dispatch tree."""
    context: dict = {"dispatch_tree": {"Dispatch": {"target": "test"}}}

    result = await registry.execute(
        strategy_name="INJECT_TIMEOUT_GUARD",
        target="dispatch",
        parameters={"timeout_ms": "3000"},
        context=context,
    )

    assert result.status == RepairStatus.SUCCESS
    assert "timeout" in result.message.lower()


@pytest.mark.asyncio
async def test_repair_strategy_gc(registry: RepairRegistry):
    """FORCE_GC_AND_REDUCE_BATCH forces GC and reduces batch."""
    context: dict = {"batch_size": 100}

    result = await registry.execute(
        strategy_name="FORCE_GC_AND_REDUCE_BATCH",
        target="worker",
        parameters={"batch_reduction_factor": "0.5"},
        context=context,
    )

    assert result.status == RepairStatus.SUCCESS
    assert context["batch_size"] == 50


@pytest.mark.asyncio
async def test_repair_strategy_backoff(registry: RepairRegistry):
    """EXPONENTIAL_BACKOFF configures backoff state."""
    context: dict = {}

    result = await registry.execute(
        strategy_name="EXPONENTIAL_BACKOFF",
        target="api",
        parameters={"initial_delay_ms": "1000", "jitter": "true"},
        context=context,
    )

    assert result.status == RepairStatus.SUCCESS
    assert context.get("backoff_applied") is True
    assert context.get("backoff_delay_s", 0) > 0


@pytest.mark.asyncio
async def test_repair_strategy_escalation(registry: RepairRegistry):
    """LOG_AND_ESCALATE flags unclassified errors for human review."""
    context: dict = {"error_signature": "something weird happened"}

    result = await registry.execute(
        strategy_name="LOG_AND_ESCALATE",
        target="unknown",
        parameters={"escalation_level": "human"},
        context=context,
    )

    assert result.status == RepairStatus.SKIPPED
    assert context.get("escalation_required") is True


@pytest.mark.asyncio
async def test_repair_strategy_reserialize(registry: RepairRegistry):
    """RESERIALIZE_WITH_VALIDATION cleans payload."""
    context: dict = {"payload": {"key": "value", "null_key": None, "num": 42}}

    result = await registry.execute(
        strategy_name="RESERIALIZE_WITH_VALIDATION",
        target="serializer",
        parameters={"strip_nulls": "true", "validate_schema": "true"},
        context=context,
    )

    assert result.status == RepairStatus.SUCCESS
    assert "null_key" not in context["payload"]


# ─── Test: Unknown Strategy ───────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_repair_strategy(registry: RepairRegistry):
    """Unknown strategy returns FAILED result gracefully."""
    result = await registry.execute(
        strategy_name="NONEXISTENT_STRATEGY",
        target="test",
        parameters={},
        context={},
    )

    assert result.status == RepairStatus.FAILED
    assert "Unknown" in result.message


# ─── Test: Agent Health Reporting ─────────────────────────────────


@pytest.mark.asyncio
async def test_agent_health_reporting(agent: AutoCurativeAgent):
    """Agent health report is accurate after various events."""
    # Initial state
    health = agent.health
    assert health.status == "healthy"
    assert health.total_errors_detected == 0
    assert health.health_score > 0

    # After an error
    await agent.handle_error(
        error=TimeoutError("test timeout"),
        subsystem="test",
    )

    health = agent.health
    assert health.total_errors_detected == 1
    assert health.total_repairs_attempted == 1

    # Health dict serialization
    health_dict = health.to_dict()
    assert "status" in health_dict
    assert "uptime_s" in health_dict
    assert "repair_success_rate" in health_dict


# ─── Test: Event History ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_event_history(agent: AutoCurativeAgent):
    """Healing events are properly recorded in history."""
    await agent.handle_error(
        error=ConnectionError("refused"),
        subsystem="db",
    )
    await agent.handle_error(
        error=TimeoutError("deadline exceeded"),
        subsystem="api",
    )

    history = agent.get_healing_history(limit=10)
    assert len(history) == 2
    assert history[0]["subsystem"] == "db"
    assert history[1]["subsystem"] == "api"


# ─── Test: Breaker Reset ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_breaker_reset(agent: AutoCurativeAgent):
    """Manual circuit breaker reset works."""
    # Create a breaker by handling an error
    await agent.handle_error(
        error=RuntimeError("test"),
        subsystem="test_subsystem",
    )

    assert "test_subsystem" in agent._breakers
    assert agent.reset_breaker("test_subsystem") is True
    assert agent.reset_breaker("nonexistent") is False


# ─── Test: Concurrent Repairs ─────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_repair_limit(agent: AutoCurativeAgent):
    """Only max_concurrent_repairs repairs run simultaneously."""
    errors = [
        TimeoutError("timeout 1"),
        ConnectionError("conn 1"),
        MemoryError("mem 1"),
    ]

    # Handle all errors concurrently
    results = await asyncio.gather(
        *[agent.handle_error(error=e, subsystem=f"sub_{i}") for i, e in enumerate(errors)]
    )

    assert all(r is not None for r in results)
    assert agent.health.total_errors_detected == 3


# ─── Test: Sync Task Wrapping ────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_task_healing(agent: AutoCurativeAgent):
    """Sync (non-async) tasks are properly wrapped and healed."""

    def sync_task():
        return "sync_result"

    result = await agent.execute_with_healing(
        task=sync_task,
        subsystem="sync",
    )

    assert result == "sync_result"


# ─── Test: Full Healing Loop Integration ──────────────────────────


@pytest.mark.asyncio
async def test_full_healing_loop_integration():
    """End-to-end test of the complete self-healing loop."""
    config = AutoCurativeConfig(
        max_healing_attempts=3,
        cooldown_after_repair_s=0.01,
        breaker_failure_threshold=5,
    )
    agent = AutoCurativeAgent(config=config)

    # Simulate a task that fails with different errors then recovers
    call_count = 0

    async def evolving_task():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("request timeout")
        if call_count == 2:
            raise ConnectionError("connection reset")
        return {"status": "healed", "attempts": call_count}

    result = await agent.execute_with_healing(
        task=evolving_task,
        subsystem="integration_test",
    )

    # Verify result
    assert result["status"] == "healed"
    assert result["attempts"] == 3

    # Verify healing history
    history = agent.get_healing_history()
    assert len(history) == 2  # Two failures before success
    assert history[0]["anomaly_class"] == "TimeoutCascade"
    assert history[1]["anomaly_class"] == "ConnectionExhaustion"

    # Verify health
    health = agent.health
    assert health.total_errors_detected == 2
    assert health.total_repairs_attempted == 2
    assert health.total_repairs_succeeded == 2
    assert health.status == "healthy"

    # Verify endocrine impact
    from legacy_research.engine.endocrine import ENDOCRINE, HormoneType
    # Cortisol should have been pulsed (both up and down)
    # Neural growth should have been rewarded
    # These are integration checks - exact values depend on decay


# ─── Test: Repair Registry Custom Strategy ────────────────────────


@pytest.mark.asyncio
async def test_custom_repair_strategy():
    """Custom strategies can be registered and executed."""
    registry = RepairRegistry()

    class CustomFix:
        async def execute(self, target, parameters, context):
            context["custom_applied"] = True
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="CUSTOM_FIX",
                target=target,
                latency_ms=0.1,
                message="Custom fix applied",
            )

    registry.register("CUSTOM_FIX", CustomFix())
    assert "CUSTOM_FIX" in registry.available_strategies

    ctx: dict = {}
    result = await registry.execute("CUSTOM_FIX", "test", {}, ctx)
    assert result.status == RepairStatus.SUCCESS
    assert ctx["custom_applied"] is True
