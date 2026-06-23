# [C5-REAL] Exergy-Maximized
"""
Ouroboros Apoptosis Taxonomy.
Defines the eviction and immortality invariants for fact nodes.
"""

from dataclasses import dataclass
from enum import Enum


class OriginType(str, Enum):
    # ── Inmortales (eviction_weight = 0.0) ──────────────────────────────────
    CORE_AXIOM = "core_axiom"            # Axiomas fundacionales del sistema
    USER_DIRECTIVE = "user_directive"    # Instrucciones explícitas del operador humano
    RED_TEAM = "red_team"                # Anticuerpos validados adversarialmente

    # ── Alta supervivencia (eviction_weight = 0.1) ───────────────────────────
    HUMAN_CURATED = "human_curated"      # Conocimiento editado manualmente
    VERIFIED_COMMIT = "verified_commit"  # Nodo respaldado por commit en trunk soberano

    # ── Supervivencia media (eviction_weight = 0.4) ──────────────────────────
    FAILURE_CLUSTER = "failure_cluster"  # Patrón emergente de fallos repetidos
    SAGA_DECISION = "saga_decision"      # Decisión cristalizada por consenso BFT

    # ── Carne de cañón (eviction_weight = 0.8) ───────────────────────────────
    AGENT_SCRATCHPAD = "agent_scratchpad"       # Working memory de un turno
    STOCHASTIC_GUESS = "stochastic_guess"       # Hipótesis no validada
    RUNTIME_ASSIMILATED = "runtime_assimilated" # Auto-asimilado sin validación humana


@dataclass(frozen=True)
class OriginPolicy:
    eviction_weight: float  # 0.0 = inmortal, 1.0 = máxima presión apoptótica
    criticality_floor: float  # Mínimo criticality asignable
    criticality_ceiling: float  # Máximo criticality asignable
    hebbiano_eligible: bool   # ¿Puede recibir refuerzo LTP?


POLICY: dict[OriginType, OriginPolicy] = {
    OriginType.CORE_AXIOM: OriginPolicy(
        eviction_weight=0.0,
        criticality_floor=1.0,
        criticality_ceiling=1.0,
        hebbiano_eligible=False,   # Ya es inmortal — el refuerzo es ruido
    ),
    OriginType.USER_DIRECTIVE: OriginPolicy(
        eviction_weight=0.0,
        criticality_floor=0.95,
        criticality_ceiling=1.0,
        hebbiano_eligible=False,
    ),
    OriginType.RED_TEAM: OriginPolicy(
        eviction_weight=0.0,
        criticality_floor=0.9,
        criticality_ceiling=1.0,
        hebbiano_eligible=False,   # Inmunidad por diseño, no por uso
    ),
    OriginType.HUMAN_CURATED: OriginPolicy(
        eviction_weight=0.1,
        criticality_floor=0.7,
        criticality_ceiling=1.0,
        hebbiano_eligible=True,
    ),
    OriginType.VERIFIED_COMMIT: OriginPolicy(
        eviction_weight=0.1,
        criticality_floor=0.65,
        criticality_ceiling=0.95,
        hebbiano_eligible=True,
    ),
    OriginType.FAILURE_CLUSTER: OriginPolicy(
        eviction_weight=0.4,
        criticality_floor=0.4,
        criticality_ceiling=0.8,
        hebbiano_eligible=True,
    ),
    OriginType.SAGA_DECISION: OriginPolicy(
        eviction_weight=0.4,
        criticality_floor=0.5,
        criticality_ceiling=0.85,
        hebbiano_eligible=True,
    ),
    OriginType.AGENT_SCRATCHPAD: OriginPolicy(
        eviction_weight=0.8,
        criticality_floor=0.0,
        criticality_ceiling=0.4,
        hebbiano_eligible=True,    # Puede ascender si resulta útil
    ),
    OriginType.STOCHASTIC_GUESS: OriginPolicy(
        eviction_weight=0.8,
        criticality_floor=0.0,
        criticality_ceiling=0.35,
        hebbiano_eligible=True,
    ),
    OriginType.RUNTIME_ASSIMILATED: OriginPolicy(
        eviction_weight=0.8,
        criticality_floor=0.0,
        criticality_ceiling=0.6,
        hebbiano_eligible=True,
    ),
}


def get_policy(origin: OriginType | str) -> OriginPolicy:
    try:
        # Handling string conversions safely
        if isinstance(origin, str):
            origin_enum = OriginType(origin)
        else:
            origin_enum = origin
        return POLICY[origin_enum]
    except ValueError:
        # Default fallback for unknown origins to ensure structural robustness (C5-REAL)
        return POLICY[OriginType.AGENT_SCRATCHPAD]


def is_immortal(origin: OriginType | str) -> bool:
    return get_policy(origin).eviction_weight == 0.0
