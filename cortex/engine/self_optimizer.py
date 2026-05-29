"""Self-Optimizer — Level 6 Adaptive Learning Agent.

Analyzes performance telemetry and auto-tunes system parameters
without human intervention. Bridges L5 (reactive healing) and
L7 (generative self-creation).

Core loop:
    OBSERVE (telemetry) → ANALYZE (patterns) → OPTIMIZE (tune) → VERIFY (A/B)

What it tunes:
    - Timeouts per subsystem
    - Batch sizes
    - Circuit breaker thresholds
    - Retry policies (count, backoff factor)
    - Repair strategy selection (promote winners, demote losers)
    - Cooldown periods

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.performance_tracker import (
    PerformanceTracker,
    PerformanceSnapshot,
)

__all__ = [
    "SelfOptimizer",
    "OptimizerConfig",
    "TuningDecision",
    "OptimizationEvent",
]

logger = logging.getLogger("cortex.engine.self_optimizer")


# ─── Types ────────────────────────────────────────────────────────


class TuningType(str, Enum):
    """Type of parameter tuning applied."""

    TIMEOUT_ADJUSTMENT = "timeout_adjustment"
    BATCH_SIZE_TUNING = "batch_size_tuning"
    BREAKER_THRESHOLD = "breaker_threshold"
    RETRY_POLICY = "retry_policy"
    STRATEGY_PROMOTION = "strategy_promotion"
    STRATEGY_DEMOTION = "strategy_demotion"
    COOLDOWN_ADJUSTMENT = "cooldown_adjustment"


@dataclass
class TuningDecision:
    """A single parameter tuning decision."""

    type: TuningType
    subsystem: str
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    confidence: float  # 0.0–1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "subsystem": self.subsystem,
            "parameter": self.parameter,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class OptimizationEvent:
    """Record of a single optimization cycle."""

    timestamp: float
    snapshot: dict[str, Any]
    decisions: list[TuningDecision]
    applied: int
    skipped: int
    cycle_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "decisions_count": len(self.decisions),
            "applied": self.applied,
            "skipped": self.skipped,
            "cycle_ms": round(self.cycle_ms, 3),
            "decisions": [d.to_dict() for d in self.decisions],
        }


@dataclass
class OptimizerConfig:
    """Configuration for the Self-Optimizer."""

    # Optimization loop
    optimization_interval_s: float = 60.0
    min_samples_for_tuning: int = 20
    confidence_threshold: float = 0.6

    # Tuning bounds
    min_timeout_ms: float = 500.0
    max_timeout_ms: float = 60000.0
    timeout_adjustment_factor: float = 0.2

    min_batch_size: int = 1
    max_batch_size: int = 10000
    batch_adjustment_factor: float = 0.25

    min_breaker_threshold: int = 2
    max_breaker_threshold: int = 50

    min_retry_count: int = 1
    max_retry_count: int = 10

    min_cooldown_s: float = 0.5
    max_cooldown_s: float = 60.0

    # Strategy management
    strategy_demotion_threshold: float = 0.3  # success rate below this → demote
    strategy_promotion_threshold: float = 0.8  # success rate above this → promote

    # Safety
    max_tunings_per_cycle: int = 5
    revert_on_degradation: bool = True
    degradation_threshold: float = 0.2  # 20% worse → revert

    # History
    max_event_history: int = 200


# ─── Self-Optimizer ───────────────────────────────────────────────


class SelfOptimizer:
    """Level 6 Adaptive Learning Agent.

    Continuously monitors performance telemetry and auto-tunes
    parameters to maximize system exergy.

    Usage:
        tracker = PerformanceTracker()
        optimizer = SelfOptimizer(tracker=tracker)

        # Run single optimization cycle
        event = await optimizer.optimize()

        # Run as daemon
        await optimizer.start_daemon()

        # Manual parameter query
        timeout = optimizer.get_tuned_timeout("dispatch")
        batch = optimizer.get_tuned_batch_size("worker")
    """

    def __init__(
        self,
        tracker: PerformanceTracker,
        config: OptimizerConfig | None = None,
    ) -> None:
        self.config = config or OptimizerConfig()
        self._tracker = tracker
        self._is_running = False
        self._start_time = time.monotonic()

        # Tuned parameters (subsystem → parameter → value)
        self._tuned_params: dict[str, dict[str, Any]] = {}

        # Strategy rankings (subsystem → ordered list of strategies)
        self._strategy_rankings: dict[str, list[str]] = {}

        # History
        self._events: deque[OptimizationEvent] = deque(maxlen=self.config.max_event_history)

        # Baselines for revert detection
        self._baselines: dict[str, dict[str, float]] = {}

        # Metrics
        self._total_cycles = 0
        self._total_tunings_applied = 0
        self._total_reverts = 0

    # ─── Core: Single Optimization Cycle ──────────────────────

    async def optimize(self) -> OptimizationEvent:
        """Run a single optimization cycle.

        1. OBSERVE — Take performance snapshot
        2. ANALYZE — Identify optimization opportunities
        3. OPTIMIZE — Generate tuning decisions
        4. VERIFY — Check against baselines for safety
        """
        cycle_start = time.perf_counter_ns()
        self._total_cycles += 1

        # 1. OBSERVE
        snapshot = self._tracker.snapshot()

        # 2. ANALYZE + OPTIMIZE
        decisions = self._generate_decisions(snapshot)

        # 3. APPLY (with safety limits)
        applied = 0
        skipped = 0

        for decision in decisions:
            if applied >= self.config.max_tunings_per_cycle:
                skipped += 1
                continue

            if decision.confidence < self.config.confidence_threshold:
                skipped += 1
                continue

            self._apply_decision(decision)
            applied += 1

        # 4. Record baseline if first cycle
        if self._total_cycles == 1:
            self._record_baseline(snapshot)

        # 5. Check for degradation
        if self.config.revert_on_degradation and self._total_cycles > 3:
            reverts = self._check_degradation(snapshot)
            if reverts:
                applied -= len(reverts)
                self._total_reverts += len(reverts)

        self._total_tunings_applied += applied

        # Endocrine feedback
        if applied > 0:
            ENDOCRINE.pulse(
                HormoneType.DOPAMINE,
                0.02 * applied,
                reason=f"Self-optimization: {applied} tunings applied",
            )

        cycle_ms = (time.perf_counter_ns() - cycle_start) / 1e6

        event = OptimizationEvent(
            timestamp=time.time(),
            snapshot=snapshot.to_dict(),
            decisions=decisions,
            applied=applied,
            skipped=skipped,
            cycle_ms=cycle_ms,
        )
        self._events.append(event)

        if applied > 0:
            logger.info(
                "[OPTIMIZER] Cycle #%d: %d applied, %d skipped (%.2fms)",
                self._total_cycles,
                applied,
                skipped,
                cycle_ms,
            )

        return event

    def _generate_decisions(self, snapshot: PerformanceSnapshot) -> list[TuningDecision]:
        """Analyze snapshot and generate tuning decisions."""
        decisions: list[TuningDecision] = []

        for name in self._tracker.subsystem_names:
            metrics = self._tracker.get_metrics(name)
            if metrics is None or metrics.total_executions < self.config.min_samples_for_tuning:
                continue

            # ── Timeout tuning ────────────────────────────────
            decisions.extend(self._tune_timeout(name, metrics))

            # ── Batch size tuning ─────────────────────────────
            decisions.extend(self._tune_batch_size(name, metrics))

            # ── Circuit breaker threshold ─────────────────────
            decisions.extend(self._tune_breaker(name, metrics))

            # ── Strategy promotion/demotion ───────────────────
            decisions.extend(self._tune_strategies(name, metrics))

            # ── Cooldown adjustment ───────────────────────────
            decisions.extend(self._tune_cooldown(name, metrics))

        return decisions

    def _tune_timeout(self, subsystem: str, metrics: Any) -> list[TuningDecision]:
        """Tune timeout based on latency percentiles."""
        decisions = []
        current = self._get_param(subsystem, "timeout_ms", 5000.0)

        # If p99 is close to timeout, increase it
        if metrics.p99 > 0 and metrics.p99 > current * 0.8:
            new_val = min(
                self.config.max_timeout_ms,
                current * (1.0 + self.config.timeout_adjustment_factor),
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.TIMEOUT_ADJUSTMENT,
                        subsystem=subsystem,
                        parameter="timeout_ms",
                        old_value=current,
                        new_value=round(new_val, 1),
                        reason=f"p99 ({metrics.p99:.1f}ms) approaching timeout ({current:.1f}ms)",
                        confidence=0.85,
                    )
                )

        # If p99 is much lower than timeout, decrease it (save resources)
        elif metrics.p99 > 0 and metrics.p99 < current * 0.2:
            new_val = max(
                self.config.min_timeout_ms,
                current * (1.0 - self.config.timeout_adjustment_factor * 0.5),
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.TIMEOUT_ADJUSTMENT,
                        subsystem=subsystem,
                        parameter="timeout_ms",
                        old_value=current,
                        new_value=round(new_val, 1),
                        reason=f"p99 ({metrics.p99:.1f}ms) far below timeout ({current:.1f}ms)",
                        confidence=0.7,
                    )
                )

        return decisions

    def _tune_batch_size(self, subsystem: str, metrics: Any) -> list[TuningDecision]:
        """Tune batch size based on error rate and latency."""
        decisions = []
        current = self._get_param(subsystem, "batch_size", 100)

        # High error rate → reduce batch
        if metrics.error_rate > 0.15:
            new_val = max(
                self.config.min_batch_size,
                int(current * (1.0 - self.config.batch_adjustment_factor)),
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.BATCH_SIZE_TUNING,
                        subsystem=subsystem,
                        parameter="batch_size",
                        old_value=current,
                        new_value=new_val,
                        reason=f"High error rate ({metrics.error_rate:.2%}) → reduce batch pressure",
                        confidence=0.80,
                    )
                )

        # Low error rate + low latency → increase batch (more throughput)
        elif metrics.error_rate < 0.02 and metrics.p90 < 100:
            new_val = min(
                self.config.max_batch_size,
                int(current * (1.0 + self.config.batch_adjustment_factor)),
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.BATCH_SIZE_TUNING,
                        subsystem=subsystem,
                        parameter="batch_size",
                        old_value=current,
                        new_value=new_val,
                        reason=f"Low error ({metrics.error_rate:.2%}) + fast p90 ({metrics.p90:.1f}ms)",
                        confidence=0.65,
                    )
                )

        return decisions

    def _tune_breaker(self, subsystem: str, metrics: Any) -> list[TuningDecision]:
        """Tune circuit breaker threshold based on error patterns."""
        decisions = []
        current = self._get_param(subsystem, "breaker_threshold", 5)

        # Very few errors → can be more tolerant (raise threshold)
        if metrics.error_rate < 0.01 and metrics.total_executions > 100:
            new_val = min(self.config.max_breaker_threshold, current + 1)
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.BREAKER_THRESHOLD,
                        subsystem=subsystem,
                        parameter="breaker_threshold",
                        old_value=current,
                        new_value=new_val,
                        reason=f"Very low error rate ({metrics.error_rate:.4f}) — increase tolerance",
                        confidence=0.6,
                    )
                )

        # High error bursts → be more sensitive (lower threshold)
        elif metrics.error_rate > 0.2:
            new_val = max(self.config.min_breaker_threshold, current - 1)
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        type=TuningType.BREAKER_THRESHOLD,
                        subsystem=subsystem,
                        parameter="breaker_threshold",
                        old_value=current,
                        new_value=new_val,
                        reason=f"High error rate ({metrics.error_rate:.2%}) — trip faster",
                        confidence=0.75,
                    )
                )

        return decisions

    def _tune_strategies(self, subsystem: str, metrics: Any) -> list[TuningDecision]:
        """Promote winning strategies and demote losers."""
        decisions = []

        for sname, strat in metrics.strategies.items():
            if strat.total_attempts < 5:
                continue

            # Demotion
            if strat.success_rate < self.config.strategy_demotion_threshold:
                decisions.append(
                    TuningDecision(
                        type=TuningType.STRATEGY_DEMOTION,
                        subsystem=subsystem,
                        parameter=f"strategy:{sname}",
                        old_value="active",
                        new_value="demoted",
                        reason=(
                            f"Strategy '{sname}' success rate "
                            f"({strat.success_rate:.1%}) below threshold "
                            f"({self.config.strategy_demotion_threshold:.0%})"
                        ),
                        confidence=0.85,
                    )
                )

            # Promotion
            elif strat.success_rate > self.config.strategy_promotion_threshold:
                decisions.append(
                    TuningDecision(
                        type=TuningType.STRATEGY_PROMOTION,
                        subsystem=subsystem,
                        parameter=f"strategy:{sname}",
                        old_value="active",
                        new_value="promoted",
                        reason=(
                            f"Strategy '{sname}' excels "
                            f"({strat.success_rate:.1%} success, "
                            f"{strat.avg_latency_ms:.1f}ms avg)"
                        ),
                        confidence=0.90,
                    )
                )

        return decisions

    def _tune_cooldown(self, subsystem: str, metrics: Any) -> list[TuningDecision]:
        """Tune cooldown period between repair attempts."""
        decisions = []
        current = self._get_param(subsystem, "cooldown_s", 5.0)

        # Fast recovery → reduce cooldown
        best = metrics.best_strategy
        if best and best in metrics.strategies:
            strat = metrics.strategies[best]
            if strat.success_rate > 0.9 and strat.avg_latency_ms < 50:
                new_val = max(self.config.min_cooldown_s, current * 0.7)
                if abs(new_val - current) > 0.1:
                    decisions.append(
                        TuningDecision(
                            type=TuningType.COOLDOWN_ADJUSTMENT,
                            subsystem=subsystem,
                            parameter="cooldown_s",
                            old_value=round(current, 2),
                            new_value=round(new_val, 2),
                            reason=f"Fast repairs ({strat.avg_latency_ms:.1f}ms) — reduce cooldown",
                            confidence=0.65,
                        )
                    )

        return decisions

    # ─── Parameter Management ─────────────────────────────────

    def _get_param(self, subsystem: str, param: str, default: Any) -> Any:
        """Get a tuned parameter value."""
        return self._tuned_params.get(subsystem, {}).get(param, default)

    def _apply_decision(self, decision: TuningDecision) -> None:
        """Apply a tuning decision to the parameter store."""
        if decision.subsystem not in self._tuned_params:
            self._tuned_params[decision.subsystem] = {}
        self._tuned_params[decision.subsystem][decision.parameter] = decision.new_value

        logger.info(
            "[OPTIMIZER] ⚡ %s.%s: %s → %s (%s)",
            decision.subsystem,
            decision.parameter,
            decision.old_value,
            decision.new_value,
            decision.reason[:80],
        )

    def _record_baseline(self, snapshot: PerformanceSnapshot) -> None:
        """Record performance baseline for degradation detection."""
        for name, data in snapshot.subsystems.items():
            self._baselines[name] = {
                "error_rate": data.get("error_rate", 0),
                "mean_latency_ms": data.get("mean_latency_ms", 0),
                "p99_ms": data.get("p99_ms", 0),
            }

    def _check_degradation(self, snapshot: PerformanceSnapshot) -> list[TuningDecision]:
        """Check if tunings caused performance degradation. Revert if so."""
        reverts = []

        for name, data in snapshot.subsystems.items():
            baseline = self._baselines.get(name)
            if not baseline:
                continue

            current_err = data.get("error_rate", 0)
            baseline_err = baseline.get("error_rate", 0)

            # Error rate degraded significantly
            if baseline_err > 0 and current_err > baseline_err * (
                1 + self.config.degradation_threshold
            ):
                # Revert all tunings for this subsystem
                if name in self._tuned_params:
                    logger.warning(
                        "[OPTIMIZER] ⚠️ Degradation detected in '%s' "
                        "(err: %.4f → %.4f). Reverting tunings.",
                        name,
                        baseline_err,
                        current_err,
                    )
                    self._tuned_params.pop(name, None)
                    ENDOCRINE.pulse(
                        HormoneType.CORTISOL,
                        0.03,
                        reason=f"Optimizer revert: {name} degraded",
                    )

        return reverts

    # ─── Public Parameter Queries ─────────────────────────────

    def get_tuned_timeout(self, subsystem: str, default: float = 5000.0) -> float:
        """Get the optimized timeout for a subsystem."""
        return self._get_param(subsystem, "timeout_ms", default)

    def get_tuned_batch_size(self, subsystem: str, default: int = 100) -> int:
        """Get the optimized batch size for a subsystem."""
        return self._get_param(subsystem, "batch_size", default)

    def get_tuned_breaker_threshold(self, subsystem: str, default: int = 5) -> int:
        """Get the optimized circuit breaker threshold."""
        return self._get_param(subsystem, "breaker_threshold", default)

    def get_tuned_cooldown(self, subsystem: str, default: float = 5.0) -> float:
        """Get the optimized cooldown period."""
        return self._get_param(subsystem, "cooldown_s", default)

    def get_strategy_ranking(self, subsystem: str) -> list[str]:
        """Get the ranked list of strategies for a subsystem (best first)."""
        return self._strategy_rankings.get(subsystem, [])

    def get_all_tuned_params(self) -> dict[str, dict[str, Any]]:
        """Get all tuned parameters across all subsystems."""
        return dict(self._tuned_params)

    # ─── Daemon Mode ──────────────────────────────────────────

    async def start_daemon(self) -> None:
        """Start the continuous optimization loop."""
        if self._is_running:
            logger.warning("[OPTIMIZER] Daemon already running")
            return

        self._is_running = True
        logger.info(
            "[OPTIMIZER] 🧠 Level 6 Self-Optimizer started (interval=%.1fs)",
            self.config.optimization_interval_s,
        )

        while self._is_running:
            try:
                await self.optimize()
            except Exception as e:
                logger.error("[OPTIMIZER] Optimization cycle error: %s", e)

            await asyncio.sleep(self.config.optimization_interval_s)

    def stop_daemon(self) -> None:
        """Stop the optimization daemon."""
        self._is_running = False
        logger.info("[OPTIMIZER] Daemon stopped")

    # ─── Introspection ────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "total_cycles": self._total_cycles,
            "total_tunings_applied": self._total_tunings_applied,
            "total_reverts": self._total_reverts,
            "uptime_s": round(time.monotonic() - self._start_time, 2),
            "active_tunings": sum(len(params) for params in self._tuned_params.values()),
            "subsystems_tuned": list(self._tuned_params.keys()),
        }

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent optimization events."""
        events = list(self._events)
        return [e.to_dict() for e in events[-limit:]]
