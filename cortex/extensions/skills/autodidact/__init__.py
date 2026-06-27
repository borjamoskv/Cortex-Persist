# [C5-REAL] Exergy-Maximized
"""
AUTODIDACT-Ω: Cognitive Ingestion Protocol
"""

from .epistemology import (
    Derived,
    EvidenceSource,
    Hypothesis,
    InferenceModel,
    Intervention,
    Invariant,
    InvariantLevel,
    Latent,
    Narrative,
    Observable,
    RawEvidence,
    compile_derived,
    compile_hypothesis,
    compile_latent,
    compile_latent_from_narrative,
    compile_narrative_from_narrative,
    compile_observable,
)

__all__ = [
    "EvidenceSource",
    "RawEvidence",
    "Observable",
    "Derived",
    "InferenceModel",
    "Latent",
    "InvariantLevel",
    "Invariant",
    "Intervention",
    "Hypothesis",
    "Narrative",
    "compile_observable",
    "compile_derived",
    "compile_latent",
    "compile_hypothesis",
    "compile_latent_from_narrative",
    "compile_narrative_from_narrative",
]
