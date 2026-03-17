"""Shannon Module — Corpus entropy and information quality measurement."""

from cortex.shannon.entropy import (
    ShannonReport,
    compute_corpus_entropy,
    compute_fact_entropy,
    diagnose_health,
)

__all__ = [
    "ShannonReport",
    "compute_corpus_entropy",
    "compute_fact_entropy",
    "diagnose_health",
]
