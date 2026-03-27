from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ActionRisk(str, Enum):
    READ_ONLY = "read_only"
    MEMORY_WRITE = "memory_write"
    FILE_WRITE = "file_write"
    SCHEMA_MUTATION = "schema_mutation"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class ExergyInput:
    prior_uncertainty: Decimal | float
    posterior_uncertainty: Decimal | float
    tokens_consumed: int
    action_risk: ActionRisk
    had_backup: bool
    touched_persistent_state: bool


@dataclass(frozen=True)
class ExergyResult:
    score: Decimal
    signal_gain: Decimal
    reversibility_penalty: Decimal
    waste_ratio: Decimal
    below_threshold: bool


class ThermodynamicWasteError(RuntimeError):
    pass


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calculate_exergy(inp: ExergyInput, threshold_min_work: Decimal | float) -> ExergyResult:
    if inp.tokens_consumed <= 0:
        raise ValueError("tokens_consumed must be > 0")

    prior = _to_decimal(inp.prior_uncertainty)
    post = _to_decimal(inp.posterior_uncertainty)
    min_work = _to_decimal(threshold_min_work)

    # Calculate signal gain with high precision
    signal_gain = max(Decimal("0"), prior - post) / Decimal(str(inp.tokens_consumed))
    risk_penalty_map = {
        ActionRisk.READ_ONLY: Decimal("0.0"),
        ActionRisk.MEMORY_WRITE: Decimal("0.05"),
        ActionRisk.FILE_WRITE: Decimal("0.15"),
        ActionRisk.SCHEMA_MUTATION: Decimal("0.45"),
        ActionRisk.DESTRUCTIVE: Decimal("0.80"),
    }

    reversibility_penalty = risk_penalty_map[inp.action_risk]

    if not inp.had_backup and inp.action_risk in {
        ActionRisk.FILE_WRITE,
        ActionRisk.SCHEMA_MUTATION,
        ActionRisk.DESTRUCTIVE,
    }:
        reversibility_penalty += Decimal("0.35")

    if inp.touched_persistent_state:
        reversibility_penalty += Decimal("0.05")

    score = signal_gain - reversibility_penalty

    if signal_gain == 0:
        waste_ratio = Decimal("0")
    else:
        waste_ratio = max(Decimal("0"), reversibility_penalty / signal_gain)

    return ExergyResult(
        score=score,
        signal_gain=signal_gain,
        reversibility_penalty=reversibility_penalty,
        waste_ratio=waste_ratio,
        below_threshold=score < min_work,
    )


def enforce_exergy(result: ExergyResult) -> None:
    if result.below_threshold:
        raise ThermodynamicWasteError(
            f"Exergy below threshold: score={result.score:.6f}, "
            f"signal_gain={result.signal_gain:.6f}, "
            f"penalty={result.reversibility_penalty:.6f}"
        )
