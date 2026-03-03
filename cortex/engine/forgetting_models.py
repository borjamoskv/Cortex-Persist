from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = ["PolicyRecommendation", "EvictionVerdict", "OracleReport"]


class PolicyRecommendation(Enum):
    """Ajuste de política sugerido por el Oracle."""

    OPTIMAL = "OPTIMAL"  # El sistema olvida correctamente
    INCREASE_TTL = "INCREASE_TTL"  # Olvida demasiado pronto (regret rate alto)
    REDUCE_CAPACITY = "REDUCE_CAPACITY"  # Olvida demasiado tarde (utilización OOM risk)
    PRIORITIZE_CAUSAL = "PRIORITIZE_CAUSAL"  # Olvida hechos causalmente críticos


@dataclass
class EvictionVerdict:
    """Resultado del análisis post-hoc de una evicción concreta."""

    key: str
    eviction_id: int
    reason: str
    was_regrettable: bool  # ¿Fue eviccionado algo que se necesitó después?
    causal_weight: float  # 0.0 = sin peso causal, 1.0 = axioma crítico
    access_frequency_score: float  # 0.0 = nunca accedido, 1.0 = muy frecuente
    eviction_value: float  # Score compuesto de qué tan costosa fue la decisión
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

    def to_dict(self) -> dict[str, Any]:
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
            "regrettable_evictions": sum(1 for v in self.verdicts if v.was_regrettable),
        }
