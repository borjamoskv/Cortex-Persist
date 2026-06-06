# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from typing import Any

from .types import OptimizerConfig, TuningDecision, TuningType


class OptimizationTuners:
    @staticmethod
    def tune_timeout(
        subsystem: str, metrics: Any, current: float, config: OptimizerConfig
    ) -> list[TuningDecision]:
        decisions = []
        if metrics.p99 > 0 and metrics.p99 > current * 0.8:
            new_val = min(config.max_timeout_ms, current * (1.0 + config.timeout_adjustment_factor))
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.TIMEOUT_ADJUSTMENT,
                        subsystem,
                        "timeout_ms",
                        current,
                        round(new_val, 1),
                        f"p99 ({metrics.p99:.1f}ms) approaching timeout ({current:.1f}ms)",
                        0.85,
                    )
                )
        elif metrics.p99 > 0 and metrics.p99 < current * 0.2:
            new_val = max(
                config.min_timeout_ms, current * (1.0 - config.timeout_adjustment_factor * 0.5)
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.TIMEOUT_ADJUSTMENT,
                        subsystem,
                        "timeout_ms",
                        current,
                        round(new_val, 1),
                        f"p99 ({metrics.p99:.1f}ms) far below timeout ({current:.1f}ms)",
                        0.7,
                    )
                )
        return decisions

    @staticmethod
    def tune_batch_size(
        subsystem: str, metrics: Any, current: int, config: OptimizerConfig
    ) -> list[TuningDecision]:
        decisions = []
        if metrics.error_rate > 0.15:
            new_val = max(
                config.min_batch_size, int(current * (1.0 - config.batch_adjustment_factor))
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.BATCH_SIZE_TUNING,
                        subsystem,
                        "batch_size",
                        current,
                        new_val,
                        f"High error rate ({metrics.error_rate:.2%}) -> reduce batch",
                        0.80,
                    )
                )
        elif metrics.error_rate < 0.02 and metrics.p90 < 100:
            new_val = min(
                config.max_batch_size, int(current * (1.0 + config.batch_adjustment_factor))
            )
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.BATCH_SIZE_TUNING,
                        subsystem,
                        "batch_size",
                        current,
                        new_val,
                        f"Low error ({metrics.error_rate:.2%}) + fast p90 ({metrics.p90:.1f}ms)",
                        0.65,
                    )
                )
        return decisions

    @staticmethod
    def tune_breaker(
        subsystem: str, metrics: Any, current: int, config: OptimizerConfig
    ) -> list[TuningDecision]:
        decisions = []
        if metrics.error_rate < 0.01 and metrics.total_executions > 100:
            new_val = min(config.max_breaker_threshold, current + 1)
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.BREAKER_THRESHOLD,
                        subsystem,
                        "breaker_threshold",
                        current,
                        new_val,
                        "Very low error rate - increase tolerance",
                        0.6,
                    )
                )
        elif metrics.error_rate > 0.2:
            new_val = max(config.min_breaker_threshold, current - 1)
            if new_val != current:
                decisions.append(
                    TuningDecision(
                        TuningType.BREAKER_THRESHOLD,
                        subsystem,
                        "breaker_threshold",
                        current,
                        new_val,
                        "High error rate - trip faster",
                        0.75,
                    )
                )
        return decisions

    @staticmethod
    def tune_strategies(
        subsystem: str, metrics: Any, config: OptimizerConfig
    ) -> list[TuningDecision]:
        decisions = []
        for sname, strat in metrics.strategies.items():
            if strat.total_attempts < 5:
                continue
            if strat.success_rate < config.strategy_demotion_threshold:
                decisions.append(
                    TuningDecision(
                        TuningType.STRATEGY_DEMOTION,
                        subsystem,
                        f"strategy:{sname}",
                        "active",
                        "demoted",
                        f"Strategy '{sname}' success rate below threshold",
                        0.85,
                    )
                )
            elif strat.success_rate > config.strategy_promotion_threshold:
                decisions.append(
                    TuningDecision(
                        TuningType.STRATEGY_PROMOTION,
                        subsystem,
                        f"strategy:{sname}",
                        "active",
                        "promoted",
                        f"Strategy '{sname}' excels",
                        0.90,
                    )
                )
        return decisions

    @staticmethod
    def tune_cooldown(
        subsystem: str, metrics: Any, current: float, config: OptimizerConfig
    ) -> list[TuningDecision]:
        decisions = []
        best = metrics.best_strategy
        if best and best in metrics.strategies:
            strat = metrics.strategies[best]
            if strat.success_rate > 0.9 and strat.avg_latency_ms < 50:
                new_val = max(config.min_cooldown_s, current * 0.7)
                if abs(new_val - current) > 0.1:
                    decisions.append(
                        TuningDecision(
                            TuningType.COOLDOWN_ADJUSTMENT,
                            subsystem,
                            "cooldown_s",
                            round(current, 2),
                            round(new_val, 2),
                            "Fast repairs - reduce cooldown",
                            0.65,
                        )
                    )
        return decisions
