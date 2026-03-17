from dataclasses import dataclass
from enum import Enum


class AgentMode(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DECORATIVE = "decorative"
    QUARANTINED = "quarantined"


@dataclass
class ThermodynamicCounters:
    consecutive_tool_fails_without_new_hypothesis: int = 0
    file_reads_without_ast_delta: int = 0
    context_expansion_rate: float = 0.0
    uncertainty_reduction_rate: float = 0.0


class DecorativeModeTriggered(RuntimeError):
    pass


def should_enter_decorative_mode(c: ThermodynamicCounters) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if c.consecutive_tool_fails_without_new_hypothesis >= 3:
        reasons.append("tool_fails_without_new_hypothesis>=3")

    if c.file_reads_without_ast_delta >= 5:
        reasons.append("file_reads_without_ast_delta>=5")

    if c.context_expansion_rate > c.uncertainty_reduction_rate:
        reasons.append("context_expansion_rate>uncertainty_reduction_rate")

    return (len(reasons) > 0, reasons)
