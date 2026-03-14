"""ENCB v2 — CRDT Merge Operators.

Layer 1: Replica convergence only. No truth resolution here.
Each merge operator is commutative, associative, and idempotent.

Merge handles what happens when two replicas see the same proposition
concurrently. The *Hypervisor* (Layer 2) decides what's actually true.
"""

from __future__ import annotations

import statistics
from typing import Any

from benchmarks.encb.belief_object import BeliefObject, BeliefType, Evidence


def merge_version_vectors(
    a: dict[str, int],
    b: dict[str, int],
) -> dict[str, int]:
    """Point-wise max of two version vectors."""
    merged: dict[str, int] = dict(a)
    for node, clock in b.items():
        merged[node] = max(merged.get(node, 0), clock)
    return merged


# ── Boolean Merge ──────────────────────────────────────────────────────────


def merge_boolean(local: BeliefObject, remote: BeliefObject) -> BeliefObject:
    """Merge two boolean beliefs using vector clock ordering.

    If one dominates: take the dominant value.
    If concurrent: keep both in conflict_set, take higher-confidence value.
    """
    assert local.belief_type == BeliefType.BOOLEAN
    assert remote.belief_type == BeliefType.BOOLEAN
    assert local.proposition_key == remote.proposition_key

    merged_vv = merge_version_vectors(
        local.version_vector, remote.version_vector
    )
    merged_evidences = _merge_evidence_lists(local.evidences, remote.evidences)

    if local.dominates(remote):
        result_value = local.value
        result_conf = local.confidence
        conflict = set(local.conflict_set)
    elif remote.dominates(local):
        result_value = remote.value
        result_conf = remote.confidence
        conflict = set(remote.conflict_set)
    else:
        # Concurrent — take higher confidence, mark conflict
        if local.confidence >= remote.confidence:
            result_value = local.value
            result_conf = local.confidence
        else:
            result_value = remote.value
            result_conf = remote.confidence
        conflict = local.conflict_set | remote.conflict_set
        if local.value != remote.value:
            conflict.add(local.belief_id)
            conflict.add(remote.belief_id)

    local.value = result_value
    local.confidence = result_conf
    local.version_vector = merged_vv
    local.evidences = merged_evidences
    local.conflict_set = conflict
    return local


# ── Categorical Merge ──────────────────────────────────────────────────────


def merge_categorical(local: BeliefObject, remote: BeliefObject) -> BeliefObject:
    """Merge two categorical beliefs.

    Uses vector clock for ordering. On concurrent writes, keeps both
    as candidates and selects by confidence.
    """
    assert local.belief_type == BeliefType.CATEGORICAL
    assert remote.belief_type == BeliefType.CATEGORICAL
    assert local.proposition_key == remote.proposition_key

    merged_vv = merge_version_vectors(
        local.version_vector, remote.version_vector
    )
    merged_evidences = _merge_evidence_lists(local.evidences, remote.evidences)

    if local.dominates(remote):
        result_value = local.value
        result_conf = local.confidence
        conflict = set(local.conflict_set)
    elif remote.dominates(local):
        result_value = remote.value
        result_conf = remote.confidence
        conflict = set(remote.conflict_set)
    else:
        # Concurrent — highest confidence wins, conflict tracked
        if local.confidence >= remote.confidence:
            result_value = local.value
            result_conf = local.confidence
        else:
            result_value = remote.value
            result_conf = remote.confidence
        conflict = local.conflict_set | remote.conflict_set
        if local.value != remote.value:
            conflict.add(local.belief_id)
            conflict.add(remote.belief_id)

    local.value = result_value
    local.confidence = result_conf
    local.version_vector = merged_vv
    local.evidences = merged_evidences
    local.conflict_set = conflict
    return local


# ── Scalar Merge ───────────────────────────────────────────────────────────


def merge_scalar(local: BeliefObject, remote: BeliefObject) -> BeliefObject:
    """Merge two scalar beliefs.

    Collects all scalar observations and uses median as the merged value
    (robust to outliers at the CRDT level). Hypervisor refines later.
    """
    assert local.belief_type == BeliefType.SCALAR
    assert remote.belief_type == BeliefType.SCALAR
    assert local.proposition_key == remote.proposition_key

    merged_vv = merge_version_vectors(
        local.version_vector, remote.version_vector
    )
    merged_evidences = _merge_evidence_lists(local.evidences, remote.evidences)

    # Collect all observed scalar values from evidence
    values: list[float] = []
    for ev in merged_evidences:
        try:
            # Extract value from payload_hash format "key:value:t:node"
            parts = ev.payload_hash.split(":")
            if len(parts) >= 2:
                values.append(float(parts[1]))
        except (ValueError, IndexError):
            pass

    if values:
        result_value = statistics.median(values)
    else:
        # Fallback — take more recent
        result_value = (
            local.value
            if local.latest_timestamp >= remote.latest_timestamp
            else remote.value
        )

    result_conf = max(local.confidence, remote.confidence)

    local.value = result_value
    local.confidence = result_conf
    local.version_vector = merged_vv
    local.evidences = merged_evidences
    local.conflict_set = local.conflict_set | remote.conflict_set
    return local


# ── Set Merge (OR-Set) ────────────────────────────────────────────────────


def merge_set(local: BeliefObject, remote: BeliefObject) -> BeliefObject:
    """Merge two set beliefs using OR-Set semantics.

    Union of both sets. Conflict_set tracks disagreements.
    Value must be a set or frozenset.
    """
    assert local.belief_type == BeliefType.SET
    assert remote.belief_type == BeliefType.SET
    assert local.proposition_key == remote.proposition_key

    merged_vv = merge_version_vectors(
        local.version_vector, remote.version_vector
    )
    merged_evidences = _merge_evidence_lists(local.evidences, remote.evidences)

    local_set = set(local.value) if local.value else set()
    remote_set = set(remote.value) if remote.value else set()

    # OR-Set: union
    merged_value = local_set | remote_set

    result_conf = max(local.confidence, remote.confidence)

    local.value = merged_value
    local.confidence = result_conf
    local.version_vector = merged_vv
    local.evidences = merged_evidences
    local.conflict_set = local.conflict_set | remote.conflict_set
    return local


# ── Dispatcher ─────────────────────────────────────────────────────────────


MERGE_FN = {
    BeliefType.BOOLEAN: merge_boolean,
    BeliefType.CATEGORICAL: merge_categorical,
    BeliefType.SCALAR: merge_scalar,
    BeliefType.SET: merge_set,
}


def merge(local: BeliefObject, remote: BeliefObject) -> BeliefObject:
    """Dispatch to the correct merge function based on belief type."""
    fn = MERGE_FN.get(local.belief_type)
    if fn is None:
        raise ValueError(f"No merge function for type {local.belief_type}")
    return fn(local, remote)


# ── Helpers ────────────────────────────────────────────────────────────────


def _merge_evidence_lists(
    a: list[Evidence],
    b: list[Evidence],
) -> list[Evidence]:
    """Deduplicated union of two evidence lists, ordered by timestamp."""
    seen: set[str] = set()
    merged: list[Evidence] = []
    for ev in sorted((*a, *b), key=lambda e: e.timestamp):
        if ev.payload_hash not in seen:
            seen.add(ev.payload_hash)
            merged.append(ev)
    return merged
