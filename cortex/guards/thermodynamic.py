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
    causal_taint_count: int = 0  # Ω₁₁: Number of tainted descendants detected


class MetastabilityProbe:
    """Detection of fragile equilibria (Ω₁₃)."""

    @staticmethod
    def probe(c: ThermodynamicCounters) -> float:
        """Calculate metastability index. 1.0 = stable, 0.0 = collapsed."""
        if c.context_expansion_rate == 0:
            return 1.0
        # If entropy grows faster than uncertainty reduction, the system is fragile.
        balance = c.uncertainty_reduction_rate / c.context_expansion_rate
        return min(1.0, balance)


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

    if c.causal_taint_count > 10:
        reasons.append("causal_taint_count>10 (systemic contamination)")

    # Metastability check
    if MetastabilityProbe.probe(c) < 0.2:
        reasons.append("metastability_index<0.2 (fragile equilibrium)")

    return (len(reasons) > 0, reasons)
