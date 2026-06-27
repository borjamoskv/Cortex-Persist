# [C5-REAL] Exergy-Maximized
"""
Epistemological Compiler (Autodidact).
This module defines the strict, causally-typed pipeline for system knowledge.
It enforces determinism and prevents invalid semantic transitions (e.g., Narrative -> Latent).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Union

from pydantic import BaseModel, Field, model_validator


class EvidenceSource(str, Enum):
    """Domains of physical reality from which raw evidence originates."""
    FILESYSTEM = "filesystem"
    GIT_OBJECTS = "git_objects"
    COMPILER_LOGS = "compiler_logs"
    CPU_COUNTERS = "cpu_counters"
    KERNEL_EVENTS = "kernel_events"


class RawEvidence(BaseModel):
    """The physical base of knowledge. Uninterpreted."""
    source: EvidenceSource
    raw_payload: dict[str, Any] | str | bytes
    timestamp_iso: str


class Observable(BaseModel):
    """The direct, deterministic consequence of an extraction algorithm on RawEvidence."""
    evidence: RawEvidence
    metric_name: str
    value: Any
    extractor_hash: str = Field(
        ..., description="Hash of the deterministic algorithm used for extraction"
    )


class Derived(BaseModel):
    """A pure function or aggregate over Observables or other Derived facts. No heuristics."""
    inputs: list[Union[Observable, 'Derived']]
    function_name: str
    value: Any


class InferenceModel(str, Enum):
    """Explicit parametric models for Latent knowledge."""
    BAYESIAN = "bayesian"
    KALMAN = "kalman"
    PARTICLE = "particle"
    NEURAL = "neural"
    RULE_BASED = "rule_based"
    CAUSAL_GRAPH = "causal_graph"


class Latent(BaseModel):
    """Probabilistic inference demanding an explicit model and confidence score."""
    inputs: list[Union[Derived, Observable]]
    model: InferenceModel
    posterior: float = Field(..., ge=0.0, le=1.0)
    inferred_state: dict[str, Any]


class InvariantLevel(str, Enum):
    """Densities of system protection."""
    HARD = "hard"
    SOFT = "soft"
    TEMPORAL = "temporal"
    PROBABILISTIC = "probabilistic"


class Invariant(BaseModel):
    """Thermodynamic contract protecting physical state."""
    level: InvariantLevel
    target_metric: str
    condition: Callable[[Any], bool]
    
    def check(self, value: Any) -> bool:
        return self.condition(value)


class Intervention(BaseModel):
    """A physical action mutating the host environment (Pearl's do-calculus)."""
    action_name: str
    parameters: dict[str, Any]
    predicted_outcomes: dict[str, Any]
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    def execute(self) -> str:
        """Physical execution placeholder (Ledger / SAGA connection)."""
        return f"do({self.action_name})"


class Hypothesis(BaseModel):
    """Maps Latent knowledge to an Intervention."""
    latent_basis: Latent
    proposed_intervention: Intervention


class Narrative(BaseModel):
    """Output rendering layer for biological entities. NOT for inference."""
    content: str
    basis: Union[Observable, Derived, Latent, Intervention]
    
    @model_validator(mode="before")
    @classmethod
    def check_invalid_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            basis = data.get("basis")
            if isinstance(basis, Narrative):
                raise ValueError("Epistemological Type Error: Narrative cannot be derived from Narrative.")
        return data


# --- Semantic Validation Enforcement (The Linter) ---

def compile_observable(evidence: RawEvidence, extractor: Callable, extractor_hash: str, name: str) -> Observable:
    """RawEvidence -> Observable (VALID)"""
    return Observable(
        evidence=evidence,
        metric_name=name,
        value=extractor(evidence.raw_payload),
        extractor_hash=extractor_hash
    )

def compile_derived(inputs: list[Union[Observable, Derived]], pure_func: Callable, name: str) -> Derived:
    """Observable/Derived -> Derived (VALID)"""
    return Derived(
        inputs=inputs,
        function_name=name,
        value=pure_func([i.value for i in inputs])
    )

def compile_latent(inputs: list[Union[Derived, Observable]], model: InferenceModel, infer_func: Callable) -> Latent:
    """Derived/Observable -> Latent (VALID)"""
    posterior, state = infer_func([i.value for i in inputs])
    return Latent(
        inputs=inputs,
        model=model,
        posterior=posterior,
        inferred_state=state
    )

def compile_hypothesis(latent: Latent, intervention: Intervention) -> Hypothesis:
    """Latent -> Hypothesis (VALID)"""
    return Hypothesis(latent_basis=latent, proposed_intervention=intervention)

def compile_narrative_from_narrative(nar: Narrative) -> None:
    """Narrative -> Narrative (INVALID)"""
    raise TypeError("Epistemological Type Error: Narrative cannot be derived from another Narrative.")

def compile_latent_from_narrative(nar: Narrative, model: InferenceModel, func: Callable) -> None:
    """Narrative -> Latent (INVALID)"""
    raise TypeError("Epistemological Type Error: Latent models cannot consume Narrative (stochastic language).")

