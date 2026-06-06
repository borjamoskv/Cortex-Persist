# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TuningType(str, Enum):
    TIMEOUT_ADJUSTMENT = "timeout_adjustment"
    BATCH_SIZE_TUNING = "batch_size_tuning"
    BREAKER_THRESHOLD = "breaker_threshold"
    RETRY_POLICY = "retry_policy"
    STRATEGY_PROMOTION = "strategy_promotion"
    STRATEGY_DEMOTION = "strategy_demotion"
    COOLDOWN_ADJUSTMENT = "cooldown_adjustment"


@dataclass
class TuningDecision:
    type: TuningType
    subsystem: str
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    confidence: float

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
    optimization_interval_s: float = 60.0
    min_samples_for_tuning: int = 20
    confidence_threshold: float = 0.6
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
    strategy_demotion_threshold: float = 0.3
    strategy_promotion_threshold: float = 0.8
    max_tunings_per_cycle: int = 5
    revert_on_degradation: bool = True
    degradation_threshold: float = 0.2
    max_event_history: int = 200
