"""CORTEX Supervisor — Central Nervous System for the Agent Stack.

Single daemon that boots, coordinates, and monitors all agents
as a unified organism:

    ┌─────────────────────────────────────────────────┐
    │              CortexSupervisor                    │
    │                                                  │
    │  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
    │  │ L5 Auto  │→→│ L6 Self  │→→│ L7 Autopoietic│  │
    │  │ Curative │←←│ Optimizer│←←│    (evolve)   │  │
    │  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
    │       │              │                │          │
    │       ▼              ▼                ▼          │
    │  ┌─────────────────────────────────────────┐     │
    │  │        Performance Tracker               │     │
    │  │        Predictive Healer                  │     │
    │  │        Tuning Store (persist)              │     │
    │  └─────────────────────────────────────────┘     │
    │                      │                           │
    │                      ▼                           │
    │              ┌──────────────┐                    │
    │              │ DoubtCircuit │ (meta-monitor)     │
    │              │   (SICA)     │                    │
    │              └──────────────┘                    │
    └─────────────────────────────────────────────────┘

Boot order: Tracker → Store → L5 → L6 → Predictor → Supervisor loop
Shutdown:   Supervisor → L6 → L5 → Persist → done

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections.abc import Callable, Coroutine

from cortex.engine.autocurative_agent import AutoCurativeAgent
from cortex.engine._autocurative_config import AutoCurativeConfig
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.performance_tracker import PerformanceTracker
from cortex.engine.predictive_healer import PredictiveHealer, Prediction
from cortex.engine.self_optimizer import SelfOptimizer, OptimizerConfig
from cortex.engine.tuning_store import TuningStore

__all__ = ["CortexSupervisor", "SupervisorConfig", "AgentStatus"]

logger = logging.getLogger("cortex.supervisor")


# ─── Types ────────────────────────────────────────────────────────


class AgentStatus(str, Enum):
    """Lifecycle status of a managed agent."""

    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentInfo:
    """Runtime info for a managed agent."""

    name: str
    level: int
    status: AgentStatus = AgentStatus.UNINITIALIZED
    boot_time: float = 0.0
    last_heartbeat: float = 0.0
    error_count: int = 0
    instance: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "status": self.status.value,
            "boot_time": round(self.boot_time, 3),
            "last_heartbeat": round(self.last_heartbeat, 2),
            "error_count": self.error_count,
            "alive": self.status == AgentStatus.RUNNING,
        }


@dataclass
class SupervisorConfig:
    """Configuration for the CortexSupervisor."""

    # Agent configs
    curative_config: AutoCurativeConfig = field(default_factory=AutoCurativeConfig)
    optimizer_config: OptimizerConfig = field(default_factory=OptimizerConfig)

    # Supervisor loop
    heartbeat_interval_s: float = 10.0
    optimization_interval_s: float = 60.0
    prediction_interval_s: float = 30.0
    persist_interval_s: float = 120.0
    health_check_interval_s: float = 15.0

    # Persistence
    persist_dir: str | None = None

    # Preemptive action
    preemptive_confidence: float = 0.75

    # Safety
    max_agent_restarts: int = 3
    agent_boot_timeout_s: float = 10.0

    # Degradation thresholds
    cortisol_alarm: float = 0.7
    health_score_critical: float = 30.0


# ─── Supervisor ───────────────────────────────────────────────────


class CortexSupervisor:
    """Central Nervous System — unified agent lifecycle manager.

    Boots, coordinates, and monitors all agents as a single organism.

    Usage:
        supervisor = CortexSupervisor()

        # Execute a task through the full stack
        result = await supervisor.execute(my_function, subsystem="api")

        # Start the autonomous daemon
        await supervisor.start()

        # Health report
        report = supervisor.health()

        # Graceful shutdown
        supervisor.shutdown()
    """

    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.config = config or SupervisorConfig()

        # ─── Infrastructure (boot first) ──────────────────
        self._tracker = PerformanceTracker()
        self._store = TuningStore(base_dir=self.config.persist_dir)
        self._predictor = PredictiveHealer(
            tracker=self._tracker,
            cortisol_threshold=self.config.cortisol_alarm,
        )

        # ─── L5: Auto-Curative Agent ─────────────────────
        self._l5 = AutoCurativeAgent(config=self.config.curative_config)

        # ─── L6: Self-Optimizer ──────────────────────────
        self._l6 = SelfOptimizer(
            tracker=self._tracker,
            config=self.config.optimizer_config,
        )

        # ─── Agent registry ──────────────────────────────
        self._agents: dict[str, AgentInfo] = {
            "tracker": AgentInfo(name="PerformanceTracker", level=0),
            "store": AgentInfo(name="TuningStore", level=0),
            "l5": AgentInfo(name="AutoCurativeAgent", level=5),
            "l6": AgentInfo(name="SelfOptimizer", level=6),
            "predictor": AgentInfo(name="PredictiveHealer", level=6),
        }

        # ─── State ───────────────────────────────────────
        self._is_running = False
        self._start_time: float = 0.0
        self._boot_sequence_completed = False
        self._total_tasks_executed = 0
        self._total_heals = 0
        self._total_predictions = 0
        self._total_preemptive_actions = 0

    # ═══════════════════════════════════════════════════════════════
    # BOOT SEQUENCE
    # ═══════════════════════════════════════════════════════════════

    async def boot(self) -> dict[str, AgentStatus]:
        """Boot all agents in dependency order.

        Order: Tracker → Store → L5 → L6 → Predictor
        Each agent is booted with health verification.
        """
        logger.info("[SUPERVISOR] ════════════════════════════════════════")
        logger.info("[SUPERVISOR] 🧠 CORTEX SUPERVISOR — BOOT SEQUENCE")
        logger.info("[SUPERVISOR] ════════════════════════════════════════")

        self._start_time = time.monotonic()
        boot_order = ["tracker", "store", "l5", "l6", "predictor"]

        for agent_key in boot_order:
            info = self._agents[agent_key]
            info.status = AgentStatus.BOOTING
            boot_start = time.perf_counter()

            try:
                await self._boot_agent(agent_key)
                info.boot_time = (time.perf_counter() - boot_start) * 1000
                info.status = AgentStatus.RUNNING
                info.last_heartbeat = time.monotonic()
                logger.info(
                    "[SUPERVISOR] ✅ L%d %s booted (%.1fms)",
                    info.level,
                    info.name,
                    info.boot_time,
                )
            except Exception as e:
                info.status = AgentStatus.FAILED
                info.error_count += 1
                logger.error(
                    "[SUPERVISOR] ❌ L%d %s FAILED: %s",
                    info.level,
                    info.name,
                    e,
                )

        self._boot_sequence_completed = True

        # Restore persisted tunings
        self._restore_tunings()

        # Endocrine signal: system alive
        ENDOCRINE.pulse(
            HormoneType.DOPAMINE,
            0.1,
            reason="Supervisor boot complete",
        )

        result = {k: v.status for k, v in self._agents.items()}
        running = sum(1 for s in result.values() if s == AgentStatus.RUNNING)
        logger.info(
            "[SUPERVISOR] Boot complete: %d/%d agents running",
            running,
            len(result),
        )

        return result

    async def _boot_agent(self, key: str) -> None:
        """Boot a specific agent with validation."""
        info = self._agents[key]

        if key == "tracker":
            info.instance = self._tracker

        elif key == "store":
            info.instance = self._store

        elif key == "l5":
            info.instance = self._l5

        elif key == "l6":
            info.instance = self._l6

        elif key == "predictor":
            info.instance = self._predictor

    def _restore_tunings(self) -> None:
        """Restore persisted tunings into L6."""
        saved = self._store.load_all()
        if saved:
            for sub, params in saved.items():
                self._l6._tuned_params[sub] = params
            self._sync_l6_to_l5()
            logger.info(
                "[SUPERVISOR] 📂 Restored tunings for %d subsystems",
                len(saved),
            )

    # ═══════════════════════════════════════════════════════════════
    # TASK EXECUTION (single entry point)
    # ═══════════════════════════════════════════════════════════════

    async def execute(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a task through the full L5+L6 stack.

        1. Inject L6-optimized parameters
        2. Execute via L5 self-healing
        3. Record telemetry for L6
        4. Feed predictor
        """
        if not self._boot_sequence_completed:
            await self.boot()

        ctx = context or {}
        start_ns = time.perf_counter_ns()

        # Inject optimized parameters from L6
        ctx["timeout_ms"] = self._l6.get_tuned_timeout(subsystem)
        ctx["batch_size"] = self._l6.get_tuned_batch_size(subsystem)
        ctx["cooldown_s"] = self._l6.get_tuned_cooldown(subsystem)

        try:
            result = await self._l5.execute_with_healing(
                task,
                *args,
                subsystem=subsystem,
                context=ctx,
                **kwargs,
            )

            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=True)
            self._total_tasks_executed += 1
            return result

        except Exception:
            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=False)
            self._predictor.record_error_event(subsystem)
            self._total_tasks_executed += 1
            raise

    # ═══════════════════════════════════════════════════════════════
    # DAEMON MODE
    # ═══════════════════════════════════════════════════════════════

    async def start(self, engine: Any = None) -> None:
        """Start the unified supervisor daemon.

        Runs all background loops concurrently:
        - L5 healing daemon
        - L6 optimization loop
        - Prediction loop
        - Health check loop
        - Persistence loop
        - Parameter sync loop
        """
        if self._is_running:
            logger.warning("[SUPERVISOR] Already running")
            return

        if not self._boot_sequence_completed:
            await self.boot()

        self._is_running = True
        logger.info("[SUPERVISOR] 🚀 Autonomous daemon started")

        await asyncio.gather(
            self._l5_daemon(engine),
            self._l6_optimization_loop(),
            self._prediction_loop(),
            self._health_check_loop(),
            self._persist_loop(),
            self._sync_loop(),
        )

    async def _l5_daemon(self, engine: Any = None) -> None:
        """Run the L5 autocurative monitoring daemon."""
        try:
            await self._l5.start_daemon(engine=engine)
        except Exception as e:
            logger.error("[SUPERVISOR] L5 daemon crashed: %s", e)
            self._agents["l5"].status = AgentStatus.FAILED
            self._agents["l5"].error_count += 1

    async def _l6_optimization_loop(self) -> None:
        """L6 optimization cycle."""
        while self._is_running:
            try:
                event = await self._l6.optimize()
                if event.applied > 0:
                    self._sync_l6_to_l5()
                    logger.info("[SUPERVISOR] L6 applied %d tunings", event.applied)
                self._agents["l6"].last_heartbeat = time.monotonic()
            except Exception as e:
                logger.error("[SUPERVISOR] L6 error: %s", e)
                self._agents["l6"].error_count += 1

            await asyncio.sleep(self.config.optimization_interval_s)

    async def _prediction_loop(self) -> None:
        """Predictive healing cycle."""
        while self._is_running:
            try:
                predictions = self._predictor.predict_all()
                self._total_predictions += len(predictions)
                critical = [
                    p
                    for p in predictions
                    if p.is_critical and p.confidence >= self.config.preemptive_confidence
                ]

                for p in critical:
                    await self._apply_preemptive_action(p)

                self._agents["predictor"].last_heartbeat = time.monotonic()

            except Exception as e:
                logger.error("[SUPERVISOR] Prediction error: %s", e)
                self._agents["predictor"].error_count += 1

            await asyncio.sleep(self.config.prediction_interval_s)

    async def _health_check_loop(self) -> None:
        """Periodic health check of all agents."""
        while self._is_running:
            try:
                for _key, info in self._agents.items():
                    if info.status == AgentStatus.RUNNING:
                        # Check heartbeat staleness
                        staleness = time.monotonic() - info.last_heartbeat
                        if staleness > self.config.health_check_interval_s * 5:
                            info.status = AgentStatus.DEGRADED
                            logger.warning(
                                "[SUPERVISOR] ⚠️ %s heartbeat stale (%.0fs)",
                                info.name,
                                staleness,
                            )

                # System-wide cortisol check
                cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)
                if cortisol > self.config.cortisol_alarm:
                    logger.warning(
                        "[SUPERVISOR] 🔴 System cortisol alarm: %.3f",
                        cortisol,
                    )

            except Exception as e:
                logger.error("[SUPERVISOR] Health check error: %s", e)

            await asyncio.sleep(self.config.health_check_interval_s)

    async def _persist_loop(self) -> None:
        """Periodic persistence of learned tunings."""
        while self._is_running:
            try:
                all_params = self._l6.get_all_tuned_params()
                if all_params:
                    self._store.snapshot(all_params, self._l6.stats)
            except Exception as e:
                logger.error("[SUPERVISOR] Persist error: %s", e)

            await asyncio.sleep(self.config.persist_interval_s)

    async def _sync_loop(self) -> None:
        """Periodic L6 → L5 parameter sync."""
        while self._is_running:
            self._sync_l6_to_l5()
            await asyncio.sleep(self.config.heartbeat_interval_s)

    # ═══════════════════════════════════════════════════════════════
    # PARAMETER SYNC (L6 → L5)
    # ═══════════════════════════════════════════════════════════════

    def _sync_l6_to_l5(self) -> None:
        """Sync ALL optimized parameters from L6 into L5."""
        all_params = self._l6.get_all_tuned_params()

        for subsystem, params in all_params.items():
            # Circuit breaker threshold
            breaker = self._l5._breakers.get(subsystem)
            if breaker is not None:
                threshold = params.get("breaker_threshold")
                if threshold is not None:
                    breaker._threshold = threshold

            # Timeout
            timeout = params.get("timeout_ms")
            if timeout is not None:
                self._l5.config.healing_timeout_s = timeout / 1000.0

            # Cooldown
            cooldown = params.get("cooldown_s")
            if cooldown is not None:
                self._l5.config.cooldown_after_repair_s = cooldown

    # ═══════════════════════════════════════════════════════════════
    # PREEMPTIVE ACTIONS
    # ═══════════════════════════════════════════════════════════════

    async def _apply_preemptive_action(self, prediction: Prediction) -> None:
        """Apply preventive measure based on prediction."""
        action = prediction.recommended_action
        sub = prediction.subsystem

        logger.warning(
            "[SUPERVISOR] 🔮 Preemptive: %s on '%s' (conf=%.2f, TTF=%.0fs)",
            action,
            sub,
            prediction.confidence,
            prediction.estimated_time_to_failure_s,
        )

        if action == "PREEMPTIVE_BATCH_REDUCTION":
            current = self._l6.get_tuned_batch_size(sub)
            new_val = max(1, int(current * 0.7))
            self._l6._tuned_params.setdefault(sub, {})["batch_size"] = new_val

        elif action == "PREEMPTIVE_TIMEOUT_INCREASE":
            current = self._l6.get_tuned_timeout(sub)
            new_val = min(60000, current * 1.3)
            self._l6._tuned_params.setdefault(sub, {})["timeout_ms"] = new_val

        elif action == "PREEMPTIVE_CONSOLIDATION":
            ENDOCRINE.pulse(
                HormoneType.SEROTONIN,
                0.1,
                reason="Preemptive consolidation trigger",
            )

        elif action == "PREEMPTIVE_BREAKER_WARMUP":
            # Pre-create circuit breaker for subsystem
            self._l5._get_or_create_breaker(sub)

        self._total_preemptive_actions += 1
        self._predictor.record_prevention()
        self._sync_l6_to_l5()

    # ═══════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ═══════════════════════════════════════════════════════════════

    def shutdown(self) -> None:
        """Graceful shutdown: stop agents + persist state."""
        logger.info("[SUPERVISOR] ════════════════════════════════════════")
        logger.info("[SUPERVISOR] 🛑 SHUTDOWN SEQUENCE")
        logger.info("[SUPERVISOR] ════════════════════════════════════════")

        self._is_running = False

        # Stop agents in reverse order
        self._l5.stop_daemon()
        self._l6.stop_daemon()

        # Persist final state
        all_params = self._l6.get_all_tuned_params()
        if all_params:
            self._store.snapshot(all_params, self._l6.stats)
            logger.info(
                "[SUPERVISOR] 💾 Final state persisted (%d subsystems)",
                len(all_params),
            )

        # Mark all as stopped
        for info in self._agents.values():
            info.status = AgentStatus.STOPPED

        ENDOCRINE.pulse(
            HormoneType.SEROTONIN,
            0.5,
            reason="Supervisor shutdown",
        )

        total_uptime = time.monotonic() - self._start_time if self._start_time else 0
        logger.info(
            "[SUPERVISOR] Shutdown complete. Uptime: %.1fs, Tasks: %d",
            total_uptime,
            self._total_tasks_executed,
        )

    # ═══════════════════════════════════════════════════════════════
    # INTROSPECTION
    # ═══════════════════════════════════════════════════════════════

    def health(self) -> dict[str, Any]:
        """Complete system health report."""
        uptime = time.monotonic() - self._start_time if self._start_time else 0

        agent_reports = {k: v.to_dict() for k, v in self._agents.items()}
        running_count = sum(1 for v in self._agents.values() if v.status == AgentStatus.RUNNING)

        # System status
        if running_count == len(self._agents):
            system_status = "healthy"
        elif running_count > 0:
            system_status = "degraded"
        else:
            system_status = "critical"

        cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)

        return {
            "status": system_status,
            "uptime_s": round(uptime, 2),
            "agents": agent_reports,
            "agents_running": running_count,
            "agents_total": len(self._agents),
            "tasks_executed": self._total_tasks_executed,
            "predictions_generated": self._total_predictions,
            "preemptive_actions": self._total_preemptive_actions,
            "cortisol": round(cortisol, 4),
            "tuned_subsystems": list(self._l6.get_all_tuned_params().keys()),
            "persisted_subsystems": self._store.subsystems,
            "l5_health": self._l5.health.to_dict(),
            "l6_stats": self._l6.stats,
            "predictor_stats": self._predictor.stats,
        }

    def status(self) -> str:
        """Quick one-line status."""
        h = self.health()
        return (
            f"[{h['status'].upper()}] "
            f"agents={h['agents_running']}/{h['agents_total']} "
            f"tasks={h['tasks_executed']} "
            f"cortisol={h['cortisol']:.3f} "
            f"uptime={h['uptime_s']:.0f}s"
        )

    # ═══════════════════════════════════════════════════════════════
    # DIRECT ACCESS (escape hatches)
    # ═══════════════════════════════════════════════════════════════

    @property
    def l5(self) -> AutoCurativeAgent:
        """Direct access to L5 Auto-Curative Agent."""
        return self._l5

    @property
    def l6(self) -> SelfOptimizer:
        """Direct access to L6 Self-Optimizer."""
        return self._l6

    @property
    def tracker(self) -> PerformanceTracker:
        """Direct access to Performance Tracker."""
        return self._tracker

    @property
    def predictor(self) -> PredictiveHealer:
        """Direct access to Predictive Healer."""
        return self._predictor

    @property
    def store(self) -> TuningStore:
        """Direct access to Tuning Store."""
        return self._store
