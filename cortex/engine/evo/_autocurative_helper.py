# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import TYPE_CHECKING, Any

from cortex.engine.evo._autocurative_state import HealingEvent, HealingPhase
from cortex.engine.uncategorized.circuit_breaker import CircuitState
from cortex.engine.uncategorized.endocrine import ENDOCRINE, HormoneType
from cortex.engine.evo.repair_strategies import RepairResult

if TYPE_CHECKING:
    from cortex.engine.swarm.autocurative_agent import AutoCurativeAgent

logger = logging.getLogger("cortex.engine.autocurative")


async def execute_with_healing(
    agent: AutoCurativeAgent,
    task: Any,
    subsystem: str = "default",
    context: dict[str, Any] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a task with the full self-healing loop."""
    breaker = agent._get_or_create_breaker(subsystem)
    ctx = context or {}
    last_error: Exception | None = None

    for attempt in range(agent.config.max_healing_attempts):
        cycle_start = time.perf_counter_ns()

        # ─── CHECK: Circuit breaker ────────────────────────
        if breaker.state == CircuitState.OPEN:
            logger.warning(
                "[AUTOCURATIVE] Circuit breaker OPEN for '%s' - skipping execution",
                subsystem,
            )
            ENDOCRINE.pulse(
                HormoneType.ADRENALINE,
                agent.config.adrenaline_on_critical,
                reason=f"Circuit OPEN: {subsystem}",
            )
            raise RuntimeError(
                f"AutoCurative: circuit breaker OPEN for '{subsystem}' "
                f"after {breaker.total_trips} trips"
            )

        # ─── EXECUTE ──────────────────────────────────────
        agent._phase = HealingPhase.EXECUTING
        try:
            if inspect.iscoroutinefunction(task):
                result = await asyncio.wait_for(
                    task(*args, **kwargs),
                    timeout=agent.config.healing_timeout_s,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(task, *args, **kwargs),
                    timeout=agent.config.healing_timeout_s,
                )

            # ─── SUCCESS ──────────────────────────────────
            agent._phase = HealingPhase.IDLE
            breaker._on_success()

            if attempt > 0:
                # Healed after previous failure
                logger.info(
                    "[AUTOCURATIVE] ✅ Task healed after %d attempt(s) in '%s'",
                    attempt,
                    subsystem,
                )
                ENDOCRINE.pulse(
                    HormoneType.NEURAL_GROWTH,
                    agent.config.neural_growth_on_heal,
                    reason=f"Self-healed: {subsystem}",
                )
                ENDOCRINE.pulse(
                    HormoneType.CORTISOL,
                    agent.config.cortisol_on_repair,
                    reason=f"Repair relief: {subsystem}",
                )

            return result

        except Exception as error:
            last_error = error
            breaker._on_failure()

            # ─── MONITOR (error detected) ─────────────────
            agent._phase = HealingPhase.MONITORING
            agent._total_errors += 1
            ENDOCRINE.pulse(
                HormoneType.CORTISOL,
                agent.config.cortisol_on_error,
                reason=f"Error in {subsystem}: {type(error).__name__}",
            )

            # ─── DIAGNOSE ─────────────────────────────────
            healing_event = await diagnose_and_repair(
                agent=agent,
                error=error,
                subsystem=subsystem,
                context=ctx,
                attempt=attempt,
                cycle_start=cycle_start,
            )

            if healing_event:
                agent._event_history.append(healing_event)

            # ─── COOLDOWN ─────────────────────────────────
            if attempt < agent.config.max_healing_attempts - 1:
                agent._phase = HealingPhase.COOLDOWN
                await asyncio.sleep(agent.config.cooldown_after_repair_s)

    # All attempts exhausted
    agent._phase = HealingPhase.IDLE
    logger.error(
        "[AUTOCURATIVE] ❌ All %d healing attempts exhausted for '%s'",
        agent.config.max_healing_attempts,
        subsystem,
    )
    ENDOCRINE.pulse(
        HormoneType.ADRENALINE,
        agent.config.adrenaline_on_critical,
        reason=f"Healing exhausted: {subsystem}",
    )

    if last_error:
        raise last_error
    raise RuntimeError(f"AutoCurative: healing exhausted for '{subsystem}'")


async def handle_error(
    agent: AutoCurativeAgent,
    error: Exception,
    subsystem: str,
    context: dict[str, Any] | None = None,
) -> HealingEvent | None:
    """Handle a single error through the diagnosis → repair pipeline."""
    ctx = context or {}
    cycle_start = time.perf_counter_ns()
    agent._total_errors += 1

    breaker = agent._get_or_create_breaker(subsystem)
    breaker._on_failure()

    event = await diagnose_and_repair(
        agent=agent,
        error=error,
        subsystem=subsystem,
        context=ctx,
        attempt=0,
        cycle_start=cycle_start,
    )

    if event:
        agent._event_history.append(event)

    return event


async def diagnose_and_repair(
    agent: AutoCurativeAgent,
    error: Exception,
    subsystem: str,
    context: dict[str, Any],
    attempt: int,
    cycle_start: int,
) -> HealingEvent | None:
    """Internal: diagnose error and apply repair strategy."""
    # ─── DIAGNOSE ─────────────────────────────────────────
    agent._phase = HealingPhase.DIAGNOSING
    error_sig = f"{type(error).__name__}: {str(error)[:500]}"

    diagnosis: dict[str, Any]
    if agent._rust_engine is not None:
        # Fast-path: Rust diagnosis
        diagnosis = dict(agent._rust_engine.diagnose(error_sig, subsystem))  # pyright: ignore[reportAttributeAccessIssue]
    else:
        # Fallback: Python diagnosis
        diagnosis = python_diagnose(error_sig, subsystem)

    anomaly_class = diagnosis.get("anomaly_class", "UnclassifiedError")
    severity = diagnosis.get("severity", 0.5)
    strategy_name = diagnosis.get("repair_strategy", "LOG_AND_ESCALATE")
    repair_params = diagnosis.get("repair_parameters", {})
    diagnosis_time_ns = diagnosis.get("diagnosis_time_ns", 0)
    is_recurring = diagnosis.get("is_recurring", False)

    logger.warning(
        "[AUTOCURATIVE] 🔍 Diagnosis [%d/%d]: %s → %s (severity=%.2f, recurring=%s)",
        attempt + 1,
        agent.config.max_healing_attempts,
        anomaly_class,
        strategy_name,
        severity,
        is_recurring,
    )

    # ─── REPAIR ───────────────────────────────────────────
    agent._phase = HealingPhase.REPAIRING
    repair_result: RepairResult | None = None

    async with agent._repair_semaphore:
        agent._total_repairs += 1
        context["error_signature"] = error_sig
        context["anomaly_class"] = anomaly_class

        repair_result = await agent._registry.execute(
            strategy_name=strategy_name,
            target=subsystem,
            parameters=repair_params,
            context=context,
        )

        if repair_result.succeeded:  # pyright: ignore[reportOptionalMemberAccess]
            agent._successful_repairs += 1
            if agent._rust_engine is not None:
                agent._rust_engine.record_repair_outcome(True)  # pyright: ignore[reportAttributeAccessIssue]
            logger.info(
                "[AUTOCURATIVE] 🔧 Repair SUCCESS: %s → %s (%.2fms)",
                strategy_name,
                repair_result.message[:100],  # pyright: ignore[reportOptionalMemberAccess]
                repair_result.latency_ms,  # pyright: ignore[reportOptionalMemberAccess]
            )
        else:
            if agent._rust_engine is not None:
                agent._rust_engine.record_repair_outcome(False)  # pyright: ignore[reportAttributeAccessIssue]
            logger.warning(
                "[AUTOCURATIVE] ⚠️ Repair FAILED: %s → %s",
                strategy_name,
                repair_result.message[:100],  # pyright: ignore[reportOptionalMemberAccess]
            )

    # ─── Build Event ──────────────────────────────────────
    total_cycle_ms = (time.perf_counter_ns() - cycle_start) / 1e6

    event = HealingEvent(
        timestamp_ns=time.time_ns(),
        phase=agent._phase,
        error_signature=error_sig,
        anomaly_class=anomaly_class,
        subsystem=subsystem,
        severity=severity,
        repair_strategy=strategy_name,
        repair_result=repair_result,
        diagnosis_time_ns=diagnosis_time_ns,
        total_cycle_ms=total_cycle_ms,
        iteration=attempt,
    )

    return event


def python_diagnose(error_signature: str, subsystem: str) -> dict[str, Any]:
    """Pure-Python fallback diagnosis when Rust engine is unavailable."""
    lower = error_signature.lower()
    patterns = [
        ("timeout", "TimeoutCascade", 0.8, "INJECT_TIMEOUT_GUARD"),
        ("memory", "MemoryLeak", 0.9, "FORCE_GC_AND_REDUCE_BATCH"),
        ("connection", "ConnectionExhaustion", 0.85, "RESET_POOL_AND_RETRY"),
        ("rate", "RateLimitBreach", 0.5, "EXPONENTIAL_BACKOFF"),
        ("assert", "InvariantViolation", 1.0, "SNAPSHOT_AND_ROLLBACK"),
        ("serial", "SerializationCorruption", 0.7, "RESERIALIZE_WITH_VALIDATION"),
        ("circuit", "CircuitBreakerTripped", 0.95, "PROBE_AND_RESET_BREAKER"),
        ("heartbeat", "HeartbeatLost", 0.75, "RESTART_HEARTBEAT_EMITTER"),
        ("entropy", "EntropySpike", 0.6, "TRIGGER_CONSOLIDATION"),
    ]

    for keyword, aclass, severity, strategy in patterns:
        if keyword in lower:
            return {
                "anomaly_class": aclass,
                "severity": severity,
                "repair_strategy": strategy,
                "repair_parameters": {},
                "diagnosis_time_ns": 0,
                "is_recurring": False,
            }

    return {
        "anomaly_class": "UnclassifiedError",
        "severity": 0.3,
        "repair_strategy": "LOG_AND_ESCALATE",
        "repair_parameters": {},
        "diagnosis_time_ns": 0,
        "is_recurring": False,
    }


async def start_daemon(
    agent: AutoCurativeAgent,
    engine: Any = None,
    project: str = "autocurative",
) -> None:
    """Start the self-healing daemon loop."""
    if agent._is_running:
        logger.warning("[AUTOCURATIVE] Daemon already running")
        return

    agent._is_running = True
    agent._start_time = time.monotonic()
    logger.info(
        "[AUTOCURATIVE] 🚀 Level 5 Self-Healing Daemon started (interval=%.1fs)",
        agent.config.monitor_interval_s,
    )

    while agent._is_running:
        try:
            agent._phase = HealingPhase.MONITORING

            # Health probe
            await probe_system_health(agent, engine)
            cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)

            # Thresholds
            if cortisol > agent.config.cortisol_alarm_threshold:
                logger.warning(
                    "[AUTOCURATIVE] ⚠️ Cortisol alarm: %.3f > %.3f",
                    cortisol,
                    agent.config.cortisol_alarm_threshold,
                )
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE,
                    0.05,
                    reason="Cortisol alarm threshold exceeded",
                )

            # Check circuit breakers
            for name, breaker in agent._breakers.items():
                if breaker.state == CircuitState.OPEN:
                    logger.warning(
                        "[AUTOCURATIVE] Circuit '%s' is OPEN (trips=%d)",
                        name,
                        breaker.total_trips,
                    )

            agent._phase = HealingPhase.IDLE

        except Exception as e:
            logger.error("[AUTOCURATIVE] Daemon probe error: %s", e)

        await asyncio.sleep(agent.config.monitor_interval_s)


async def probe_system_health(agent: AutoCurativeAgent, engine: Any) -> dict[str, Any]:
    """Probe the CORTEX engine's health subsystems."""
    health: dict[str, Any] = {"status": "healthy", "timestamp": time.time()}

    if engine is not None:
        try:
            if hasattr(engine, "health_check"):
                h = await asyncio.wait_for(engine.health_check(), timeout=5.0)
                health.update(h if isinstance(h, dict) else {"engine_status": str(h)})
        except Exception as e:
            health["status"] = "degraded"
            health["error"] = str(e)

    return health
