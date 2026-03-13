from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = ["PolicyRecommendation", "EvictionVerdict", "OracleReport"]


class PolicyRecommendation(Enum):
    """Ajuste de política sugerido por el Oracle."""

    OPTIMAL = "OPTIMAL"
    INCREASE_TTL = "INCREASE_TTL"
    REDUCE_CAPACITY = "REDUCE_CAPACITY"
    PRIORITIZE_CAUSAL = "PRIORITIZE_CAUSAL"
    PROTECT_CAUSAL_ROOTS = "PROTECT_CAUSAL_ROOTS"


@dataclass
class EvictionVerdict:
    """Resultado del análisis post-hoc de una evicción concreta."""

    key: str
    eviction_id: int
    reason: str
    was_regrettable: bool
    causal_weight: float  # 0.0→1.0 (type + depth bonus)
    causal_depth: int  # descendant count (0 = leaf)
    access_frequency_score: float  # 0.0→1.0
    eviction_value: float  # composite cost score
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class OracleReport:
    """Informe completo de una sesión de auditoría del Oracle."""

    audited_at: float
    window_size: int
    verdicts: list[EvictionVerdict]
    regret_rate: float
    avg_eviction_value: float
    recommendation: PolicyRecommendation
    suggested_ttl_delta: float  # +N segundos o -N segundos
    suggested_capacity_delta: int  # +N items o -N items
    evidence_chain_valid: bool
    evidence_tip: str
    system_load_factor: float = 1.0  # OS-level pressure factor (sysload)

    def to_dict(self) -> dict[str, Any]:
        regrettable = [
            v for v in self.verdicts if v.was_regrettable
        ]
        causal_roots = [
            v for v in regrettable if v.causal_depth > 0
        ]
        return {
            "audited_at": self.audited_at,
            "window_size": self.window_size,
            "regret_rate": self.regret_rate,
            "avg_eviction_value": self.avg_eviction_value,
            "recommendation": self.recommendation.value,
            "suggested_ttl_delta": self.suggested_ttl_delta,
            "suggested_capacity_delta": self.suggested_capacity_delta,
            "evidence_chain_valid": self.evidence_chain_valid,
            "evidence_tip": self.evidence_tip,
            "verdict_count": len(self.verdicts),
            "regrettable_evictions": len(regrettable),
            "causal_root_evictions": len(causal_roots),
        }
