from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ImmunityState(str, Enum):
    OBSERVED = "observed"
    QUARANTINED = "quarantined"
    PROMOTABLE = "promotable"
    SEALED = "sealed"
    NECROTIC = "necrotic"
    AMPUTATED = "amputated"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PathogenProfile:
    entropy_score: float
    contradiction_density: float
    provenance_confidence: float
    mutation_risk: float
    replication_potential: float
    causal_reach: float
    reversibility: float
    thermal_cost: float

    def composite_risk(self) -> float:
        return (
            self.entropy_score * 0.16
            + self.contradiction_density * 0.18
            + (1.0 - self.provenance_confidence) * 0.18
            + self.mutation_risk * 0.16
            + self.replication_potential * 0.20
            + self.causal_reach * 0.07
            + (1.0 - self.reversibility) * 0.03
            + self.thermal_cost * 0.02
        )


@dataclass()
class ImmuneArtifact:
    artifact_id: str
    artifact_type: str
    payload: Mapping[str, Any]
    state: ImmunityState = ImmunityState.OBSERVED
    profile: PathogenProfile | None = None
    reasons: list[str] = field(default_factory=list)
    sealed_at: str | None = None
    parent_ids: list[str] = field(default_factory=list)


class GuardViolation(Exception):
    pass


class SealViolation(Exception):
    pass


@dataclass(frozen=True)
class SealRecord:
    artifact_id: str
    content_hash: str
    parent_hashes: tuple[str, ...]
    policy_version: str
    sealed_at: str
