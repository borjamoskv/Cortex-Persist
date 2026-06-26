# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

from cortex.engine.uncategorized.endocrine import ENDOCRINE, HormoneType
from cortex.engine.uncategorized.performance_tracker import PerformanceSnapshot, PerformanceTracker

from .tuners import OptimizationTuners
from .types import OptimizationEvent, OptimizerConfig, TuningDecision

logger = logging.getLogger("cortex.engine.self_optimizer")


class SelfOptimizer:
    def __init__(self, tracker: PerformanceTracker, config: OptimizerConfig | None = None) -> None:
        self.config = config or OptimizerConfig()
        self._tracker = tracker
        self._is_running = False
        self._start_time = time.monotonic()
        self._tuned_params: dict[str, dict[str, Any]] = {}
        self._strategy_rankings: dict[str, list[str]] = {}
        self._events: deque[OptimizationEvent] = deque(maxlen=self.config.max_event_history)
        self._baselines: dict[str, dict[str, float]] = {}
        self._total_cycles = 0
        self._total_tunings_applied = 0
        self._total_reverts = 0

    async def optimize(self) -> OptimizationEvent:
        cycle_start = time.perf_counter_ns()
        self._total_cycles += 1
        snapshot = self._tracker.snapshot()
        decisions = self._generate_decisions(snapshot)

        applied = 0
        skipped = 0

        for decision in decisions:
            if (
                applied >= self.config.max_tunings_per_cycle
                or decision.confidence < self.config.confidence_threshold
            ):
                skipped += 1
                continue
            self._apply_decision(decision)
            applied += 1

        if self._total_cycles == 1:
            self._record_baseline(snapshot)

        if self.config.revert_on_degradation and self._total_cycles > 3:
            reverts = self._check_degradation(snapshot)
            if reverts:
                applied -= len(reverts)
                self._total_reverts += len(reverts)

        self._total_tunings_applied += applied

        if applied > 0:
            ENDOCRINE.pulse(
                HormoneType.DOPAMINE,
                0.02 * applied,
                reason=f"Self-optimization: {applied} tunings applied",
            )

        cycle_ms = (time.perf_counter_ns() - cycle_start) / 1e6
        event = OptimizationEvent(
            time.time(), snapshot.to_dict(), decisions, applied, skipped, cycle_ms
        )
        self._events.append(event)
        return event

    def _generate_decisions(self, snapshot: PerformanceSnapshot) -> list[TuningDecision]:
        decisions = []
        for name in self._tracker.subsystem_names:
            metrics = self._tracker.get_metrics(name)
            if metrics is None or metrics.total_executions < self.config.min_samples_for_tuning:
                continue

            decisions.extend(
                OptimizationTuners.tune_timeout(
                    name, metrics, self.get_tuned_timeout(name), self.config
                )
            )
            decisions.extend(
                OptimizationTuners.tune_batch_size(
                    name, metrics, self.get_tuned_batch_size(name), self.config
                )
            )
            decisions.extend(
                OptimizationTuners.tune_breaker(
                    name, metrics, self.get_tuned_breaker_threshold(name), self.config
                )
            )
            decisions.extend(OptimizationTuners.tune_strategies(name, metrics, self.config))
            decisions.extend(
                OptimizationTuners.tune_cooldown(
                    name, metrics, self.get_tuned_cooldown(name), self.config
                )
            )
        return decisions

    def _apply_decision(self, decision: TuningDecision) -> None:
        if decision.subsystem not in self._tuned_params:
            self._tuned_params[decision.subsystem] = {}
        self._tuned_params[decision.subsystem][decision.parameter] = decision.new_value
        logger.info(
            "[OPTIMIZER] %s.%s: %s -> %s",
            decision.subsystem,
            decision.parameter,
            decision.old_value,
            decision.new_value,
        )

    def _record_baseline(self, snapshot: PerformanceSnapshot) -> None:
        for name, data in snapshot.subsystems.items():
            self._baselines[name] = {
                "error_rate": data.get("error_rate", 0),
                "mean_latency_ms": data.get("mean_latency_ms", 0),
                "p99_ms": data.get("p99_ms", 0),
            }

    def _check_degradation(self, snapshot: PerformanceSnapshot) -> list[TuningDecision]:
        reverts = []
        for name, data in snapshot.subsystems.items():
            baseline = self._baselines.get(name)
            if not baseline:
                continue
            current_err = data.get("error_rate", 0)
            baseline_err = baseline.get("error_rate", 0)
            if baseline_err > 0 and current_err > baseline_err * (
                1 + self.config.degradation_threshold
            ):
                if name in self._tuned_params:
                    self._tuned_params.pop(name, None)
                    ENDOCRINE.pulse(
                        HormoneType.CORTISOL, 0.03, reason=f"Optimizer revert: {name} degraded"
                    )
                    # Placeholder for valid TuningDecision returns
        return reverts

    def get_tuned_timeout(self, subsystem: str, default: float = 5000.0) -> float:
        return self._tuned_params.get(subsystem, {}).get("timeout_ms", default)

    def get_tuned_batch_size(self, subsystem: str, default: int = 100) -> int:
        return self._tuned_params.get(subsystem, {}).get("batch_size", default)

    def get_tuned_breaker_threshold(self, subsystem: str, default: int = 5) -> int:
        return self._tuned_params.get(subsystem, {}).get("breaker_threshold", default)

    def get_tuned_cooldown(self, subsystem: str, default: float = 5.0) -> float:
        return self._tuned_params.get(subsystem, {}).get("cooldown_s", default)

    def get_strategy_ranking(self, subsystem: str) -> list[str]:
        return self._strategy_rankings.get(subsystem, [])

    def get_all_tuned_params(self) -> dict[str, dict[str, Any]]:
        return dict(self._tuned_params)

    async def start_daemon(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            try:
                await self.optimize()
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.error("[OPTIMIZER] cycle error: %s", e)
            await asyncio.sleep(self.config.optimization_interval_s)

    def stop_daemon(self) -> None:
        self._is_running = False

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_cycles": self._total_cycles,
            "total_tunings_applied": self._total_tunings_applied,
            "total_reverts": self._total_reverts,
            "uptime_s": round(time.monotonic() - self._start_time, 2),
            "active_tunings": sum(len(params) for params in self._tuned_params.values()),
            "subsystems_tuned": list(self._tuned_params.keys()),
        }

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in list(self._events)[-limit:]]
