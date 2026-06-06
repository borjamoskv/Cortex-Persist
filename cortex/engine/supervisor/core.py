# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.engine.autocurative_agent import AutoCurativeAgent
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.performance_tracker import PerformanceTracker
from cortex.engine.predictive_healer import PredictiveHealer
from cortex.engine.self_optimizer import SelfOptimizer
from cortex.engine.tuning_store import TuningStore

from .daemon import SupervisorDaemon
from .types import AgentInfo, AgentStatus, SupervisorConfig

logger = logging.getLogger("cortex.supervisor")


class CortexSupervisor:
    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.config = config or SupervisorConfig()
        self._tracker = PerformanceTracker()
        self._store = TuningStore(base_dir=self.config.persist_dir)
        self._predictor = PredictiveHealer(
            tracker=self._tracker, cortisol_threshold=self.config.cortisol_alarm
        )
        self._l5 = AutoCurativeAgent(config=self.config.curative_config)
        self._l6 = SelfOptimizer(tracker=self._tracker, config=self.config.optimizer_config)

        self._agents: dict[str, AgentInfo] = {
            "tracker": AgentInfo(name="PerformanceTracker", level=0),
            "store": AgentInfo(name="TuningStore", level=0),
            "l5": AgentInfo(name="AutoCurativeAgent", level=5),
            "l6": AgentInfo(name="SelfOptimizer", level=6),
            "predictor": AgentInfo(name="PredictiveHealer", level=6),
        }

        self._is_running = False
        self._start_time: float = 0.0
        self._boot_sequence_completed = False
        self._total_tasks_executed = 0
        self._total_heals = 0
        self._total_predictions = 0
        self._total_preemptive_actions = 0
        self._daemon = SupervisorDaemon(self)

    async def boot(self) -> dict[str, AgentStatus]:
        logger.info("[SUPERVISOR] BOOT SEQUENCE")
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
            except Exception as e:
                info.status = AgentStatus.FAILED
                info.error_count += 1
                logger.error("[SUPERVISOR] L%d %s FAILED: %s", info.level, info.name, e)
        self._boot_sequence_completed = True
        self._restore_tunings()
        ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.1, reason="Supervisor boot complete")
        return {k: v.status for k, v in self._agents.items()}

    async def _boot_agent(self, key: str) -> None:
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
        saved = self._store.load_all()
        if saved:
            for sub, params in saved.items():
                self._l6._tuned_params[sub] = params
            self._sync_l6_to_l5()

    async def execute(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not self._boot_sequence_completed:
            await self.boot()
        ctx = context or {}
        start_ns = time.perf_counter_ns()
        ctx["timeout_ms"] = self._l6.get_tuned_timeout(subsystem)
        ctx["batch_size"] = self._l6.get_tuned_batch_size(subsystem)
        ctx["cooldown_s"] = self._l6.get_tuned_cooldown(subsystem)
        try:
            result = await self._l5.execute_with_healing(
                task, *args, subsystem=subsystem, context=ctx, **kwargs
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

    async def start(self, engine: Any = None) -> None:
        if self._is_running:
            return
        if not self._boot_sequence_completed:
            await self.boot()
        self._is_running = True
        logger.info("[SUPERVISOR] Autonomous daemon started")
        await asyncio.gather(
            self._daemon._l5_daemon(engine),
            self._daemon._l6_optimization_loop(),
            self._daemon._prediction_loop(),
            self._daemon._health_check_loop(),
            self._daemon._persist_loop(),
            self._daemon._sync_loop(),
        )

    def _sync_l6_to_l5(self) -> None:
        all_params = self._l6.get_all_tuned_params()
        for subsystem, params in all_params.items():
            breaker = self._l5._breakers.get(subsystem)
            if breaker is not None:
                threshold = params.get("breaker_threshold")
                if threshold is not None:
                    breaker._threshold = threshold
            timeout = params.get("timeout_ms")
            if timeout is not None:
                self._l5.config.healing_timeout_s = timeout / 1000.0
            cooldown = params.get("cooldown_s")
            if cooldown is not None:
                self._l5.config.cooldown_after_repair_s = cooldown

    async def _apply_preemptive_action(self, prediction: 'Prediction') -> None:  # pyright: ignore[reportUndefinedVariable]
        """Test proxy for the daemon method."""
        await self._daemon._apply_preemptive_action(prediction)

    def shutdown(self) -> None:
        self._is_running = False
        self._l5.stop_daemon()
        self._l6.stop_daemon()
        all_params = self._l6.get_all_tuned_params()
        if all_params:
            self._store.snapshot(all_params, self._l6.stats)
        for info in self._agents.values():
            info.status = AgentStatus.STOPPED
        ENDOCRINE.pulse(HormoneType.SEROTONIN, 0.5, reason="Supervisor shutdown")

    def health(self) -> dict[str, Any]:
        uptime = time.monotonic() - self._start_time if self._start_time else 0
        agent_reports = {k: v.to_dict() for k, v in self._agents.items()}
        running_count = sum(1 for v in self._agents.values() if v.status == AgentStatus.RUNNING)
        system_status = (
            "healthy"
            if running_count == len(self._agents)
            else ("degraded" if running_count > 0 else "critical")
        )
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
        h = self.health()
        return f"[{h['status'].upper()}] agents={h['agents_running']}/{h['agents_total']} tasks={h['tasks_executed']} cortisol={h['cortisol']:.3f} uptime={h['uptime_s']:.0f}s"

    @property
    def l5(self) -> AutoCurativeAgent:
        return self._l5

    @property
    def l6(self) -> SelfOptimizer:
        return self._l6

    @property
    def tracker(self) -> PerformanceTracker:
        return self._tracker

    @property
    def predictor(self) -> PredictiveHealer:
        return self._predictor

    @property
    def store(self) -> TuningStore:
        return self._store
