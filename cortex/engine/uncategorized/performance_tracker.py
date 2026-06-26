# [C5-REAL] Exergy-Maximized
"""Performance Tracker - Telemetry Collection for Level 6 Self-Optimization.

Collects, aggregates, and analyzes execution telemetry to feed
the Self-Optimizer's parameter tuning loop.

Tracks per-subsystem:
    - Latency percentiles (p50, p90, p99)
    - Error rates (windowed)
    - Repair success rates per strategy
    - Throughput (ops/sec)
    - Resource utilization signals

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "PerformanceSnapshot",
    "PerformanceTracker",
    "StrategyEffectiveness",
    "SubsystemMetrics",
]

logger = logging.getLogger("cortex.engine.uncategorized.performance_tracker")

# ─── Types ────────────────────────────────────────────────────────


@dataclass
class StrategyEffectiveness:
    """Tracks effectiveness of a single repair strategy."""

    strategy: str
    total_attempts: int = 0
    successes: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.total_attempts)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(1, self.total_attempts)

    def record(self, success: bool, latency_ms: float) -> None:
        self.total_attempts += 1
        if success:
            self.successes += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "total_attempts": self.total_attempts,
            "successes": self.successes,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 3),
            "min_latency_ms": round(self.min_latency_ms, 3)
            if self.min_latency_ms != float("inf")
            else 0.0,
            "max_latency_ms": round(self.max_latency_ms, 3),
        }


@dataclass
class SubsystemMetrics:
    """Aggregated metrics for a single subsystem."""

    subsystem: str
    _latencies: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    _errors: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    _successes: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    total_executions: int = 0
    total_errors: int = 0
    total_successes: int = 0
    strategies: dict[str, StrategyEffectiveness] = field(default_factory=dict)

    def record_execution(self, latency_ms: float, success: bool) -> None:
        """Record an execution event."""
        now = time.monotonic()
        self._latencies.append(latency_ms)
        self.total_executions += 1
        if success:
            self._successes.append(now)
            self.total_successes += 1
        else:
            self._errors.append(now)
            self.total_errors += 1

    def record_repair(self, strategy: str, success: bool, latency_ms: float) -> None:
        """Record a repair attempt."""
        if strategy not in self.strategies:
            self.strategies[strategy] = StrategyEffectiveness(strategy=strategy)
        self.strategies[strategy].record(success, latency_ms)

    @property
    def error_rate(self) -> float:
        return self.total_errors / max(1, self.total_executions)

    def percentile(self, p: float) -> float:
        """Calculate latency percentile (0-100)."""
        if not self._latencies:
            return 0.0
        sorted_lats = sorted(self._latencies)
        idx = int(len(sorted_lats) * p / 100.0)
        idx = min(idx, len(sorted_lats) - 1)
        return sorted_lats[idx]

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p90(self) -> float:
        return self.percentile(90)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def mean_latency(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    @property
    def stddev_latency(self) -> float:
        if len(self._latencies) < 2:
            return 0.0
        mean = self.mean_latency
        variance = sum((x - mean) ** 2 for x in self._latencies) / len(self._latencies)
        return math.sqrt(variance)

    @property
    def best_strategy(self) -> str | None:
        """Return the strategy with highest success rate."""
        if not self.strategies:
            return None
        return max(
            self.strategies.values(),
            key=lambda s: (s.success_rate, -s.avg_latency_ms),
        ).strategy

    def to_dict(self) -> dict[str, Any]:
        return {
            "subsystem": self.subsystem,
            "total_executions": self.total_executions,
            "total_errors": self.total_errors,
            "error_rate": round(self.error_rate, 4),
            "p50_ms": round(self.p50, 3),
            "p90_ms": round(self.p90, 3),
            "p99_ms": round(self.p99, 3),
            "mean_latency_ms": round(self.mean_latency, 3),
            "stddev_latency_ms": round(self.stddev_latency, 3),
            "best_strategy": self.best_strategy,
            "strategies": {k: v.to_dict() for k, v in self.strategies.items()},
        }


@dataclass
class PerformanceSnapshot:
    """Point-in-time snapshot of all system performance."""

    timestamp: float
    subsystems: dict[str, dict[str, Any]]
    global_error_rate: float
    global_mean_latency_ms: float
    global_p99_ms: float
    optimization_opportunities: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "subsystems": self.subsystems,
            "global_error_rate": round(self.global_error_rate, 4),
            "global_mean_latency_ms": round(self.global_mean_latency_ms, 3),
            "global_p99_ms": round(self.global_p99_ms, 3),
            "optimization_opportunities": self.optimization_opportunities,
        }


# ─── Tracker ──────────────────────────────────────────────────────


class PerformanceTracker:
    """Centralized performance telemetry collector.

    Collects per-subsystem metrics and generates periodic snapshots
    that the Self-Optimizer uses to drive parameter tuning.
    """

    def __init__(self, snapshot_window: int = 1000) -> None:
        self._subsystems: dict[str, SubsystemMetrics] = {}
        self._snapshots: deque[PerformanceSnapshot] = deque(maxlen=100)
        self._snapshot_window = snapshot_window

    def _get_or_create(self, subsystem: str) -> SubsystemMetrics:
        if subsystem not in self._subsystems:
            self._subsystems[subsystem] = SubsystemMetrics(subsystem=subsystem)
        return self._subsystems[subsystem]

    def record_execution(self, subsystem: str, latency_ms: float, success: bool) -> None:
        """Record an execution event for a subsystem."""
        self._get_or_create(subsystem).record_execution(latency_ms, success)

    def record_repair(
        self,
        subsystem: str,
        strategy: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record a repair attempt for a subsystem."""
        self._get_or_create(subsystem).record_repair(strategy, success, latency_ms)

    def get_metrics(self, subsystem: str) -> SubsystemMetrics | None:
        """Get metrics for a specific subsystem."""
        return self._subsystems.get(subsystem)

    def snapshot(self) -> PerformanceSnapshot:
        """Take a point-in-time performance snapshot."""
        now = time.time()
        subsystem_dicts = {name: m.to_dict() for name, m in self._subsystems.items()}

        # Global aggregates
        total_exec = sum(m.total_executions for m in self._subsystems.values())
        total_err = sum(m.total_errors for m in self._subsystems.values())
        global_error_rate = total_err / max(1, total_exec)

        all_means = [m.mean_latency for m in self._subsystems.values() if m.total_executions > 0]
        global_mean = sum(all_means) / max(1, len(all_means))

        all_p99 = [m.p99 for m in self._subsystems.values() if m.total_executions > 0]
        global_p99 = max(all_p99) if all_p99 else 0.0

        # Detect optimization opportunities
        opportunities = self._detect_opportunities()

        snap = PerformanceSnapshot(
            timestamp=now,
            subsystems=subsystem_dicts,
            global_error_rate=global_error_rate,
            global_mean_latency_ms=global_mean,
            global_p99_ms=global_p99,
            optimization_opportunities=opportunities,
        )
        self._snapshots.append(snap)
        return snap

    def _detect_opportunities(self) -> list[dict[str, Any]]:
        """Analyze metrics to detect optimization opportunities."""
        opportunities = []

        for name, m in self._subsystems.items():
            if m.total_executions < 10:
                continue

            # High error rate
            if m.error_rate > 0.1:
                opportunities.append(
                    {
                        "type": "HIGH_ERROR_RATE",
                        "subsystem": name,
                        "value": m.error_rate,
                        "threshold": 0.1,
                        "suggestion": "Increase retry count or adjust timeout",
                    }
                )

            # High latency variance (unstable)
            if m.stddev_latency > m.mean_latency * 0.5 and m.mean_latency > 0:
                opportunities.append(
                    {
                        "type": "HIGH_LATENCY_VARIANCE",
                        "subsystem": name,
                        "value": m.stddev_latency / m.mean_latency,
                        "threshold": 0.5,
                        "suggestion": "Stabilize with circuit breaker or batch reduction",
                    }
                )

            # p99 >> p50 (tail latency problem)
            if m.p50 > 0 and m.p99 > m.p50 * 10:
                opportunities.append(
                    {
                        "type": "TAIL_LATENCY",
                        "subsystem": name,
                        "value": m.p99 / m.p50,
                        "threshold": 10,
                        "suggestion": "Add timeout guard or investigate slow path",
                    }
                )

            # Underperforming strategy
            for sname, strat in m.strategies.items():
                if strat.total_attempts >= 5 and strat.success_rate < 0.5:
                    opportunities.append(
                        {
                            "type": "WEAK_STRATEGY",
                            "subsystem": name,
                            "strategy": sname,
                            "success_rate": strat.success_rate,
                            "suggestion": f"Replace '{sname}' with alternative strategy",
                        }
                    )

        return opportunities

    @property
    def subsystem_names(self) -> list[str]:
        return list(self._subsystems.keys())

    @property
    def history(self) -> list[PerformanceSnapshot]:
        return list(self._snapshots)

    def reset(self) -> None:
        """Reset all metrics."""
        self._subsystems.clear()
        self._snapshots.clear()
