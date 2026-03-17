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


@dataclass(frozen=True)
class ExergyResult:
    score: float
    signal_gain: float
    reversibility_penalty: float
    waste_ratio: float
    below_threshold: bool


class ThermodynamicWasteError(RuntimeError):
    pass


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

    if not inp.had_backup and inp.action_risk in {ActionRisk.FILE_WRITE, ActionRisk.SCHEMA_MUTATION, ActionRisk.DESTRUCTIVE}:
        reversibility_penalty += 0.35

    if inp.touched_persistent_state:
        reversibility_penalty += 0.05

    score = signal_gain - reversibility_penalty
    waste_ratio = 0.0 if signal_gain == 0 else max(0.0, reversibility_penalty / max(signal_gain, 1e-9))

    return ExergyResult(
        score=score,
        signal_gain=signal_gain,
        reversibility_penalty=reversibility_penalty,
        waste_ratio=waste_ratio,
        below_threshold=score < threshold_min_work,
    )


def enforce_exergy(result: ExergyResult) -> None:
    if result.below_threshold:
        raise ThermodynamicWasteError(
            f"Exergy below threshold: score={result.score:.6f}, "
            f"signal_gain={result.signal_gain:.6f}, "
            f"penalty={result.reversibility_penalty:.6f}"
        )
