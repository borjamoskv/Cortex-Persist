from decimal import Decimal
# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import datetime
import json
import time
from collections.abc import Mapping
from typing import Any

from babylon60.crypto.hash_registry import cortex_hash
from babylon60.guards.landauer_guard import LandauerGuard
from babylon60.security.types import (
    ImmuneArtifact,
    ImmunityState,
    PathogenProfile,
    RiskLevel,
    SealRecord,
    SealViolation,
)

# ---------- 5. State machine ----------

# Valid Transitions
VALID_TRANSITIONS = {
    ImmunityState.OBSERVED: {ImmunityState.QUARANTINED, ImmunityState.PROMOTABLE},
    ImmunityState.QUARANTINED: {ImmunityState.PROMOTABLE, ImmunityState.NECROTIC},
    ImmunityState.PROMOTABLE: {ImmunityState.SEALED, ImmunityState.QUARANTINED},
    ImmunityState.SEALED: {ImmunityState.NECROTIC},
    ImmunityState.NECROTIC: {ImmunityState.AMPUTATED},
    ImmunityState.AMPUTATED: set(),
}


def can_transition(current: ImmunityState, target: ImmunityState) -> bool:
    """Verifies if the immunological state transition is valid."""
    if current == target:
        return True
    return target in VALID_TRANSITIONS.get(current, set())


def transition_artifact(
    artifact: ImmuneArtifact, target: ImmunityState, reason: str | None = None
) -> None:
    """Transitions an artifact state if valid."""
    if not can_transition(artifact.state, target):
        raise ValueError(f"Invalid immunity transition: {artifact.state.value} -> {target.value}")
    artifact.state = target
    if reason:
        artifact.reasons.append(reason)


# ---------- 7. Decision policy ----------


def classify_risk(score: Decimal) -> RiskLevel:
    if score >= 0.85:
        return RiskLevel.CRITICAL
    if score >= 0.65:
        return RiskLevel.HIGH
    if score >= 0.40:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def next_state_from_profile(profile: PathogenProfile) -> ImmunityState:
    score = profile.composite_risk()
    risk = classify_risk(score)

    if risk is RiskLevel.CRITICAL:
        return ImmunityState.NECROTIC
    if risk is RiskLevel.HIGH:
        return ImmunityState.QUARANTINED
    if risk is RiskLevel.MEDIUM:
        return ImmunityState.QUARANTINED
    return ImmunityState.PROMOTABLE


# ---------- 8. Formal distinction: Guard vs Seal ----------


def run_guard_checks(payload: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []

    if "schema_version" not in payload:
        violations.append("missing_schema_version")

    if "source" not in payload:
        violations.append("missing_provenance_source")

    return violations


# ---------- 9. Semantic necrosis ----------


def detect_necrosis(
    contradiction_density: float,
    provenance_confidence: float,
    infected_ancestors_ratio: float,
    rewrite_count: int,
) -> bool:
    return (
        contradiction_density > 0.70
        or provenance_confidence < 0.30
        or infected_ancestors_ratio > 0.20
        or rewrite_count >= 4
    )


def is_necrotic(
    profile: PathogenProfile, infected_ancestors_ratio: float, rewrite_count: int
) -> bool:
    return detect_necrosis(
        contradiction_density=profile.contradiction_density,
        provenance_confidence=profile.provenance_confidence,
        infected_ancestors_ratio=infected_ancestors_ratio,
        rewrite_count=rewrite_count,
    )


# ---------- 12. Missing hooks in runtime ----------


def profile_artifact(payload: Mapping[str, Any]) -> PathogenProfile:
    """
    Evaluates the payload and returns a thermodynamic/immunological risk profile.
    This function should be expanded with real modeling logic.
    By default, returns moderate risk based on heuristics.
    """
    # Placeholder for actual analysis
    entropy = payload.get("measured_entropy", 0.5)
    contradiction = payload.get("contradiction_density", 0.0)
    provenance = 1.0 if "source" in payload else 0.5

    return PathogenProfile(
        entropy_score=entropy,
        contradiction_density=contradiction,
        provenance_confidence=provenance,
        mutation_risk=0.5,
        replication_potential=0.5,
        causal_reach=0.5,
        reversibility=0.8,
        thermal_cost=0.1,
    )


def classify_artifact(profile: PathogenProfile, payload: Mapping[str, Any]) -> ImmunityState:
    """Classifies artifact state. Promotes to SEALED if it passes HaikuGuard (Ω₄)."""
    state = next_state_from_profile(profile)

    # Landauer Immunity (Ω₄): Sacred facts that are dense/compressed are SEALED immediately.
    if LandauerGuard.validate(payload.get("content", "")):
        if payload.get("fact_type") == "axiom" or "sacred" in payload.get("tags", []):
            return ImmunityState.SEALED

    return state


def seal_artifact(artifact: ImmuneArtifact) -> SealRecord:
    if artifact.state != ImmunityState.PROMOTABLE:
        raise SealViolation("Artifact must be promotable to be sealed.")

    content_hash = cortex_hash(json.dumps(artifact.payload, sort_keys=True).encode())
    sealed_at = datetime.datetime.fromtimestamp(
        time.monotonic(), tz=datetime.timezone.utc
    ).isoformat()

    artifact.state = ImmunityState.SEALED
    artifact.sealed_at = sealed_at

    return SealRecord(
        artifact_id=artifact.artifact_id,
        content_hash=content_hash,
        parent_hashes=tuple(artifact.parent_ids),
        policy_version="v0.1",
        sealed_at=sealed_at,
    )


def assert_not_mutated(seal: SealRecord, payload: Mapping[str, Any]) -> None:
    content_hash = cortex_hash(json.dumps(payload, sort_keys=True).encode())
    if content_hash != seal.content_hash:
        raise SealViolation(f"Sealed artifact {seal.artifact_id} has been mutated.")


def can_propagate(state: ImmunityState) -> bool:
    return state in {ImmunityState.PROMOTABLE, ImmunityState.SEALED}


def verify_block_lineage(block_id: str) -> list[str]:
    """Verifies if there are contaminated ancestors in the block lineage (Placeholder)."""
    return []


def verify_necrosis_propagation(block_id: str) -> list[str]:
    """Monitors if necrosis propagates from a block to its descendants (Placeholder)."""
    return []
