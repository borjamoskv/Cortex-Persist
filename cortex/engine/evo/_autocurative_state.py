# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from cortex.engine.evo.repair_strategies import RepairResult


class HealingPhase(str, Enum):
    """Current phase of the self-healing loop."""

    IDLE = "idle"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    DIAGNOSING = "diagnosing"
    REPAIRING = "repairing"
    VERIFYING = "verifying"
    COOLDOWN = "cooldown"


@dataclass
class HealingEvent:
    """Record of a single healing cycle."""

    timestamp_ns: int
    phase: HealingPhase
    error_signature: str
    anomaly_class: str
    subsystem: str
    severity: float
    repair_strategy: str
    repair_result: RepairResult | None
    diagnosis_time_ns: int
    total_cycle_ms: float
    iteration: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "phase": self.phase.value,
            "error_signature": self.error_signature[:200],
            "anomaly_class": self.anomaly_class,
            "subsystem": self.subsystem,
            "severity": self.severity,
            "repair_strategy": self.repair_strategy,
            "repair_result": self.repair_result.to_dict() if self.repair_result else None,
            "diagnosis_time_ns": self.diagnosis_time_ns,
            "total_cycle_ms": self.total_cycle_ms,
            "iteration": self.iteration,
        }


@dataclass
class AgentHealth:
    """Overall health state of the Auto-Curative Agent."""

    status: str  # "healthy" | "degraded" | "critical" | "healing"
    uptime_s: float
    total_errors_detected: int
    total_repairs_attempted: int
    total_repairs_succeeded: int
    active_circuit_breakers: dict[str, str]
    cortisol_level: float
    health_score: float
    recent_events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "uptime_s": round(self.uptime_s, 2),
            "total_errors_detected": self.total_errors_detected,
            "total_repairs_attempted": self.total_repairs_attempted,
            "total_repairs_succeeded": self.total_repairs_succeeded,
            "repair_success_rate": (
                self.total_repairs_succeeded / max(1, self.total_repairs_attempted)
            ),
            "active_circuit_breakers": self.active_circuit_breakers,
            "cortisol_level": round(self.cortisol_level, 4),
            "health_score": round(self.health_score, 2),
            "recent_events_count": len(self.recent_events),
        }
