# [C5-REAL] Exergy-Maximized

from .benchmark import replay_episode, run_episode
from .entropy import (
    ShannonReport,
    compute_corpus_entropy,
    compute_fact_entropy,
    diagnose_health,
)
from .exergy import ActionRisk, ExergyInput, ExergyResult, calculate_exergy, enforce_exergy
from .maxwell import MaxwellDemonResult, filter_context
from .registry import make
from .verification import (
    CrossVerifier,
    DivergenceDetail,
    DivergenceType,
    ExecutionVerdict,
)

__all__ = [
    "ShannonReport",
    "compute_character_entropy",
    "compute_corpus_entropy",
    "compute_fact_entropy",
    "diagnose_health",
    "ActionRisk",
    "ExergyInput",
    "ExergyResult",
    "calculate_exergy",
    "enforce_exergy",
    "MaxwellDemonResult",
    "filter_context",
    "make",
    "run_episode",
    "replay_episode",
    "CrossVerifier",
    "DivergenceType",
    "DivergenceDetail",
    "ExecutionVerdict",
]

