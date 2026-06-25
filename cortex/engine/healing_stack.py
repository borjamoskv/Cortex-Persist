# [C5-REAL] Exergy-Maximized
"""Unified Self-Healing Stack v2 - L5 + L6 + Predictive + Persistent.

Upgrades from v1:
    1. FULL parameter sync (timeout, batch, cooldown, breaker - not just breaker)
    2. Predictive healing (trend analysis → preemptive repair)
    3. Persistence (tunings survive restart)
    4. Repair telemetry feedback to L6 tracker

    L5: EXECUTE → MONITOR → DIAGNOSE → REPAIR
                    ↓ (telemetry)
    L6: OBSERVE → ANALYZE → OPTIMIZE → VERIFY
                    ↓ (trends)
    PREDICT: TRENDS → FORECAST → PREVENT
                    ↓ (tunings)
    PERSIST: SAVE → LOAD → RESTORE

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from cortex.engine._autocurative_config import AutoCurativeConfig
from cortex.engine.autocurative_agent import AutoCurativeAgent
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.performance_tracker import PerformanceTracker
from cortex.engine.predictive_healer import Prediction, PredictiveHealer
from cortex.engine.self_optimizer import OptimizerConfig, SelfOptimizer
from cortex.engine.tuning_store import TuningStore

__all__ = ["HealingStack", "HealingStackConfig"]

logger = logging.getLogger("cortex.engine.healing_stack")


class HealingStackConfig:
    """Unified configuration for the L5+L6+Predictive+Persistent stack."""

    def __init__(
        self,
        curative_config: AutoCurativeConfig | None = None,
        optimizer_config: OptimizerConfig | None = None,
        sync_interval_s: float = 30.0,
        prediction_interval_s: float = 15.0,
        persist_interval_s: float = 120.0,
        persist_dir: str | Path | None = None,
        enable_prediction: bool = True,
        enable_persistence: bool = True,
        preemptive_action_confidence: float = 0.75,
    ) -> None:
        self.curative = curative_config or AutoCurativeConfig()
        self.optimizer = optimizer_config or OptimizerConfig()
        self.sync_interval_s = sync_interval_s
        self.prediction_interval_s = prediction_interval_s
        self.persist_interval_s = persist_interval_s
        self.persist_dir = persist_dir
        self.enable_prediction = enable_prediction
        self.enable_persistence = enable_persistence
        self.preemptive_action_confidence = preemptive_action_confidence


class HealingStack:
    """Unified L5 + L6 + Predictive + Persistent daemon.

    Usage:
        stack = HealingStack()

        # Execute with self-healing + auto-optimization + prediction
        result = await stack.execute(
            task=my_function,
            subsystem="api",
        )

        # Run as unified daemon
        await stack.start()

        # Query optimized parameters
        timeout = stack.get_timeout("api")

        # Get failure predictions
        predictions = stack.predict()
    """

    def __init__(self, config: HealingStackConfig | None = None) -> None:
        self._config = config or HealingStackConfig()

        # Core components
        self._tracker = PerformanceTracker()
        self._optimizer = SelfOptimizer(
            tracker=self._tracker,
            config=self._config.optimizer,
        )
        self._agent = AutoCurativeAgent(
            config=self._config.curative,
        )

        # Predictive healer
        self._predictor = PredictiveHealer(tracker=self._tracker)

        # Persistence
        self._store: TuningStore | None = None
        if self._config.enable_persistence:
            self._store = TuningStore(base_dir=self._config.persist_dir)
            self._restore_tunings()

        self._is_running = False
        self._start_time = time.monotonic()

    def _restore_tunings(self) -> None:
        """Restore previously persisted tunings on startup."""
        if self._store is None:
            return

        saved = self._store.load_all()
        if saved:
            for sub, params in saved.items():
                self._optimizer._tuned_params[sub] = params
            logger.info(
                "[HEALING_STACK] Restored tunings for %d subsystems: %s",
                len(saved),
                list(saved.keys()),
            )
            # Sync restored params into L5
            self._sync_parameters_sync()

    async def execute(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute with L5 healing + L6 telemetry + prediction.

        1. Check predictions for preemptive action
        2. Apply optimized parameters from L6
        3. Execute via L5 self-healing loop
        4. Record telemetry for L6 + prediction
        5. Record repair outcomes for strategy learning
        """
        ctx = context or {}
        start_ns = time.perf_counter_ns()

        # Inject ALL optimized parameters
        ctx["timeout_ms"] = self._optimizer.get_tuned_timeout(subsystem)
        ctx["batch_size"] = self._optimizer.get_tuned_batch_size(subsystem)
        ctx["cooldown_s"] = self._optimizer.get_tuned_cooldown(subsystem)

        try:
            result = await self._agent.execute_with_healing(
                task,
                *args,
                subsystem=subsystem,
                context=ctx,
                **kwargs,
            )

            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=True)

            # Feed repair telemetry from healing events
            self._feed_repair_telemetry(subsystem)

            return result

        except (ValueError, RuntimeError, TypeError, asyncio.TimeoutError):
            latency_ms = (time.perf_counter_ns() - start_ns) / 1e6
            self._tracker.record_execution(subsystem, latency_ms, success=False)
            self._predictor.record_error_event(subsystem)
            self._feed_repair_telemetry(subsystem)
            raise

    def _feed_repair_telemetry(self, subsystem: str) -> None:
        """Extract repair outcomes from L5 events and feed to L6 tracker."""
        history = self._agent.get_healing_history(limit=5)
        for event in history:
            if event.get("subsystem") != subsystem:
                continue
            repair = event.get("repair_result")
            if repair:
                self._tracker.record_repair(
                    subsystem=subsystem,
                    strategy=event.get("repair_strategy", "unknown"),
                    success=repair.get("status") == "SUCCESS",
                    latency_ms=repair.get("latency_ms", 0.0),
                )

    # ─── Prediction ───────────────────────────────────────────

    def predict(self) -> list[Prediction]:
        """Run all prediction models."""
        return self._predictor.predict_all()

    async def _prediction_loop(self) -> None:
        """Continuously predict and log warnings."""
        while self._is_running:
            try:
                predictions = self._predictor.predict_all()
                critical = [p for p in predictions if p.is_critical]

                if critical:
                    logger.warning(
                        "[HEALING_STACK] 🔮 %d critical predictions detected",
                        len(critical),
                    )
                    for p in critical:
                        logger.warning(
                            "  ⚡ %s.%s: TTF=%.0fs conf=%.2f → %s",
                            p.subsystem,
                            p.type,
                            p.estimated_time_to_failure_s,
                            p.confidence,
                            p.recommended_action,
                        )
                        # Apply preemptive action if confidence is high enough
                        if p.confidence >= self._config.preemptive_action_confidence:
                            await self._apply_preemptive_action(p)

            except (ValueError, RuntimeError, TypeError) as e:
                logger.error("[HEALING_STACK] Prediction error: %s", e)

            await asyncio.sleep(self._config.prediction_interval_s)

    async def _apply_preemptive_action(self, prediction: Prediction) -> None:
        """Apply a preemptive repair based on a prediction."""
        action = prediction.recommended_action
        sub = prediction.subsystem

        if action == "PREEMPTIVE_BATCH_REDUCTION":
            current = self._optimizer.get_tuned_batch_size(sub)
            new_val = max(1, int(current * 0.7))
            self._optimizer._tuned_params.setdefault(sub, {})["batch_size"] = new_val
            logger.info("[PREEMPTIVE] Batch %s: %d → %d", sub, current, new_val)

        elif action == "PREEMPTIVE_TIMEOUT_INCREASE":
            current = self._optimizer.get_tuned_timeout(sub)
            new_val = min(60000, current * 1.3)
            self._optimizer._tuned_params.setdefault(sub, {})["timeout_ms"] = new_val
            logger.info("[PREEMPTIVE] Timeout %s: %.0f → %.0f", sub, current, new_val)

        elif action == "PREEMPTIVE_CONSOLIDATION":
            ENDOCRINE.pulse(
                HormoneType.SEROTONIN,
                0.1,
                reason="Preemptive consolidation trigger",
            )

        self._predictor.record_prevention()
        self._sync_parameters_sync()

    # ─── Persistence ──────────────────────────────────────────

    async def _persist_loop(self) -> None:
        """Periodically persist optimizer tunings to disk."""
        while self._is_running:
            try:
                if self._store is not None:
                    all_params = self._optimizer.get_all_tuned_params()
                    if all_params:
                        self._store.snapshot(all_params, self._optimizer.stats)
            except (OSError, ValueError, TypeError) as e:
                logger.error("[HEALING_STACK] Persist error: %s", e)

            await asyncio.sleep(self._config.persist_interval_s)

    def persist_now(self) -> None:
        """Force immediate persistence of current tunings."""
        if self._store is not None:
            all_params = self._optimizer.get_all_tuned_params()
            if all_params:
                self._store.snapshot(all_params, self._optimizer.stats)

    # ─── Parameter Sync (FULL) ────────────────────────────────

    def _sync_parameters_sync(self) -> None:
        """Sync ALL L6 optimized params into L5 agent config (synchronous)."""
        all_params = self._optimizer.get_all_tuned_params()

        for subsystem, params in all_params.items():
            # Sync circuit breaker threshold
            breaker = self._agent._breakers.get(subsystem)
            if breaker is not None:
                new_threshold = params.get("breaker_threshold")
                if new_threshold is not None:
                    breaker._threshold = new_threshold

            # Sync timeout into agent config
            new_timeout = params.get("timeout_ms")
            if new_timeout:
                self._agent.config.healing_timeout_ms = int(new_timeout)
                
            new_cooldown = params.get("cooldown_s")
            if new_cooldown:
                self._agent.config.cooldown_after_repair_ms = int(new_cooldown * 1000)

    async def _sync_parameters(self) -> None:
        """Async wrapper for parameter sync."""
        self._sync_parameters_sync()

    # ─── Daemon ───────────────────────────────────────────────

    async def start(self, engine: Any = None) -> None:
        """Start the unified L5+L6+Predictive+Persistent daemon."""
        if self._is_running:
            return

        self._is_running = True
        logger.info("[HEALING_STACK] 🚀 L5+L6+Predict+Persist unified daemon started")

        tasks = [
            self._agent.start_daemon(engine=engine),
            self._optimizer_loop(),
            self._sync_loop(),
        ]

        if self._config.enable_prediction:
            tasks.append(self._prediction_loop())

        if self._config.enable_persistence and self._store is not None:
            tasks.append(self._persist_loop())

        await asyncio.gather(*tasks)

    async def _optimizer_loop(self) -> None:
        while self._is_running:
            try:
                event = await self._optimizer.optimize()
                if event.applied > 0:
                    await self._sync_parameters()
            except (ValueError, RuntimeError, KeyError) as e:
                logger.error("[HEALING_STACK] Optimizer error: %s", e)
            await asyncio.sleep(self._config.optimizer.optimization_interval_s)

    async def _sync_loop(self) -> None:
        while self._is_running:
            await self._sync_parameters()
            await asyncio.sleep(self._config.sync_interval_s)

    def stop(self) -> None:
        """Stop the unified daemon and persist final state."""
        self._is_running = False
        self._agent.stop_daemon()
        self._optimizer.stop_daemon()
        self.persist_now()
        logger.info("[HEALING_STACK] Daemon stopped. Tunings persisted.")

    # ─── Parameter Queries ────────────────────────────────────

    def get_timeout(self, subsystem: str) -> float:
        return self._optimizer.get_tuned_timeout(subsystem)

    def get_batch_size(self, subsystem: str) -> int:
        return self._optimizer.get_tuned_batch_size(subsystem)

    def get_cooldown(self, subsystem: str) -> float:
        return self._optimizer.get_tuned_cooldown(subsystem)

    # ─── Introspection ────────────────────────────────────────

    @property
    def health(self) -> dict[str, Any]:
        """Combined health from all layers."""
        agent_health = self._agent.health.to_dict()
        optimizer_stats = self._optimizer.stats
        predictor_stats = self._predictor.stats
        snapshot = self._tracker.snapshot().to_dict() if self._tracker.subsystem_names else {}

        return {
            "agent": agent_health,
            "optimizer": optimizer_stats,
            "predictor": predictor_stats,
            "telemetry": snapshot,
            "persisted_subsystems": (self._store.subsystems if self._store else []),
            "uptime_s": round(time.monotonic() - self._start_time, 2),
        }
