# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionRisk(str, Enum):
    READ_ONLY = "read_only"
    MEMORY_WRITE = "memory_write"
    FILE_WRITE = "file_write"
    SCHEMA_MUTATION = "schema_mutation"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ExergyInput:
    prior_uncertainty: float
    posterior_uncertainty: float
    tokens_consumed: int
    action_risk: ActionRisk
    had_backup: bool
    touched_persistent_state: bool
    utility_delta: float = 0.0
    causal_gap: float = 0.0


@dataclass(frozen=True)
class ExergyResult:
    score: float
    signal_gain: float
    reversibility_penalty: float
    waste_ratio: float
    below_threshold: bool
    exergy_score: float = 0.0


class ThermodynamicWasteError(RuntimeError):
    """Raised when the calculated exergy score falls below the required threshold."""


def calculate_exergy(inp: ExergyInput, threshold_min_work: float) -> ExergyResult:
    if inp.tokens_consumed <= 0:
        raise ValueError("tokens_consumed must be > 0")

    signal_gain = max(0.0, inp.prior_uncertainty - inp.posterior_uncertainty) / inp.tokens_consumed

    risk_penalty_map = {
        ActionRisk.READ_ONLY: 0.0,
        ActionRisk.MEMORY_WRITE: 0.05,
        ActionRisk.FILE_WRITE: 0.15,
        ActionRisk.SCHEMA_MUTATION: 0.45,
        ActionRisk.DESTRUCTIVE: 0.80,
    }

    reversibility_penalty = risk_penalty_map[inp.action_risk]

    if not inp.had_backup and inp.action_risk in {
        ActionRisk.FILE_WRITE,
        ActionRisk.SCHEMA_MUTATION,
        ActionRisk.DESTRUCTIVE,
    }:
        reversibility_penalty += 0.35

    # AX-047 Limerence Penalty: "La limerencia epistémica quema cuota sin mutar el estado"
    if inp.action_risk == ActionRisk.READ_ONLY and not inp.touched_persistent_state:
        limerence_penalty = 0.5
    else:
        limerence_penalty = 0.0

    total_penalty = min(0.99, reversibility_penalty + limerence_penalty)
    # Base impact from signal and causal gap
    impact = (signal_gain * (1.0 + inp.utility_delta)) + (inp.causal_gap * 0.1)
    
    # State mutation bonus (rewarding deterministic state changes)
    mutation_bonus = 1.5 if inp.touched_persistent_state else 1.0

    # Thermodynamically aligned Exergy formula: Impact discounted by entropy/risk
    exergy_score = (impact * mutation_bonus) * (1.0 - total_penalty)

    waste_ratio = (
        0.0 if signal_gain == 0 else max(0.0, total_penalty / max(signal_gain, 1e-9))
    )

    return ExergyResult(
        score=exergy_score,
        signal_gain=signal_gain,
        reversibility_penalty=reversibility_penalty,
        waste_ratio=waste_ratio,
        below_threshold=exergy_score < threshold_min_work,
        exergy_score=exergy_score,
    )


def enforce_exergy(result: ExergyResult) -> None:
    if result.below_threshold:
        raise ThermodynamicWasteError(
            f"Exergy below threshold: score={result.score:.6f}, "
            f"signal_gain={result.signal_gain:.6f}, "
            f"penalty={result.reversibility_penalty:.6f}"
        )


@dataclass(frozen=True)
class InformationalExergyResult:
    info_exergy: float
    verifiable_transformations: int
    context_useful_tokens: int
    contextual_entropy: float


def calculate_informational_exergy(
    verifiable_transformations: int,
    context_useful_tokens: int,
    contextual_entropy: float = 0.0
) -> InformationalExergyResult:
    """
    Calculates Informational Exergy (InfoEx) as defined in E-INFO-01.
    
    InfoEx = C_v / T_u
    Alternatively, IE = V / H (if contextual_entropy > 0)
    
    Where:
      - C_v (verifiable_transformations): Verifiable transformations produced (e.g., successful commits, passing tests).
      - T_u (context_useful_tokens): Useful context tokens consumed.
      - H (contextual_entropy): The measured thermodynamic entropy of the context (semantic noise).
    """
    if context_useful_tokens <= 0 and contextual_entropy <= 0:
        raise ValueError("Either context_useful_tokens or contextual_entropy must be > 0")

    # If entropy is provided and significant, use V/H, else use V/Tu
    if contextual_entropy > 0:
        info_exergy = verifiable_transformations / contextual_entropy
    else:
        info_exergy = verifiable_transformations / context_useful_tokens

    return InformationalExergyResult(
        info_exergy=info_exergy,
        verifiable_transformations=verifiable_transformations,
        context_useful_tokens=context_useful_tokens,
        contextual_entropy=contextual_entropy
    )
