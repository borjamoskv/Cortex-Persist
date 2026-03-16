# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Tests for BeliefObject contract — frozen dataclasses, enums, provenance."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from cortex.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    BeliefStatus,
    BeliefVerdict,
    ProvenanceChain,
    ProvenanceEntry,
    VerdictAction,
)

# ─── BeliefConfidence ───────────────────────────────────────────────────────


class TestBeliefConfidence:
    def test_values(self):
        assert BeliefConfidence.C1_HYPOTHESIS.value == "C1"
        assert BeliefConfidence.C5_AXIOMATIC.value == "C5"

    def test_from_string(self):
        assert BeliefConfidence("C3") == BeliefConfidence.C3_PROBABLE


# ─── BeliefStatus ───────────────────────────────────────────────────────────


class TestBeliefStatus:
    def test_lifecycle_states(self):
        assert BeliefStatus.ACTIVE.value == "active"
        assert BeliefStatus.QUARANTINED.value == "quarantined"
        assert BeliefStatus.DEPRECATED.value == "deprecated"
        assert BeliefStatus.CONTESTED.value == "contested"


# ─── ProvenanceEntry ────────────────────────────────────────────────────────


class TestProvenanceEntry:
    def test_frozen(self):
        entry = ProvenanceEntry(
            source_type="fact",
            source_id="fact-123",
            model="deep_think",
            timestamp="2026-03-14T00:00:00Z",
            action="created",
        )
        with pytest.raises(FrozenInstanceError):
            entry.action = "revised"  # type: ignore[misc]

    def test_valid_actions(self):
        for action in ("created", "supported", "contested", "revised"):
            entry = ProvenanceEntry(
                source_type="belief",
                source_id="b-1",
                model=None,
                timestamp="2026-01-01T00:00:00Z",
                action=action,
            )
            assert entry.action == action


# ─── ProvenanceChain ────────────────────────────────────────────────────────


class TestProvenanceChain:
    def test_empty_chain(self):
        chain = ProvenanceChain()
        assert len(chain) == 0
        assert list(chain) == []

    def test_extend_is_immutable(self):
        chain = ProvenanceChain()
        entry = ProvenanceEntry(
            source_type="fact",
            source_id="f-1",
            model="opus",
            timestamp="2026-03-14T00:00:00Z",
            action="created",
        )
        new_chain = chain.extend(entry)
        assert len(chain) == 0  # Original unchanged
        assert len(new_chain) == 1
        assert new_chain.entries[0] is entry

    def test_multiple_extends(self):
        chain = ProvenanceChain()
        for i in range(5):
            chain = chain.extend(
                ProvenanceEntry(
                    source_type="fact",
                    source_id=f"f-{i}",
                    model=None,
                    timestamp=f"2026-03-14T00:0{i}:00Z",
                    action="created",
                )
            )
        assert len(chain) == 5


# ─── BeliefObject ───────────────────────────────────────────────────────────


class TestBeliefObject:
    def test_creation_defaults(self):
        belief = BeliefObject(
            content="The launch is Q2 2026",
            project="cortex",
        )
        assert belief.confidence == BeliefConfidence.C2_TENTATIVE
        assert belief.status == BeliefStatus.ACTIVE
        assert belief.revision_count == 0
        assert belief.contradicts == ()
        assert belief.supported_by == ()
        assert belief.arbitrated_by is None
        assert belief.tenant_id == "default"

    def test_frozen(self):
        belief = BeliefObject(content="test", project="p")
        with pytest.raises(FrozenInstanceError):
            belief.content = "altered"  # type: ignore[misc]

    def test_is_axiomatic(self):
        belief = BeliefObject(
            content="Entropy always increases",
            project="physics",
            confidence=BeliefConfidence.C5_AXIOMATIC,
        )
        assert belief.is_axiomatic() is True

    def test_is_quarantined(self):
        belief = BeliefObject(
            content="Contradicted claim",
            project="test",
            status=BeliefStatus.QUARANTINED,
        )
        assert belief.is_quarantined() is True

    def test_replace_creates_new(self):
        original = BeliefObject(content="v1", project="test")
        revised = replace(original, content="v2", revision_count=1)
        assert original.content == "v1"
        assert revised.content == "v2"
        assert revised.revision_count == 1

    def test_serialization_roundtrip(self):
        entry = ProvenanceEntry(
            source_type="model_inference",
            source_id="agent:gemini",
            model="gemini",
            timestamp="2026-03-14T00:00:00Z",
            action="created",
        )
        provenance = ProvenanceChain(entries=(entry,))
        belief = BeliefObject(
            content="SQLite is the persistence layer",
            project="cortex",
            confidence=BeliefConfidence.C4_CONFIRMED,
            provenance=provenance,
            contradicts=("belief-old-1",),
            supported_by=("fact-99", "fact-100"),
            arbitrated_by="deep_think",
        )

        data = belief.to_dict()
        restored = BeliefObject.from_dict(data)

        assert restored.content == belief.content
        assert restored.confidence == belief.confidence
        assert restored.contradicts == belief.contradicts
        assert restored.supported_by == belief.supported_by
        assert restored.arbitrated_by == belief.arbitrated_by
        assert len(restored.provenance) == 1
        assert restored.provenance.entries[0].model == "gemini"

    def test_id_is_time_sortable(self):
        b1 = BeliefObject(content="first", project="test")
        b2 = BeliefObject(content="second", project="test")
        # IDs should be lexicographically sortable by time prefix
        assert b1.id[:14] <= b2.id[:14]


# ─── BeliefVerdict ──────────────────────────────────────────────────────────


class TestBeliefVerdict:
    def test_accept_verdict(self):
        verdict = BeliefVerdict(
            action=VerdictAction.ACCEPT,
            model="deep_think",
        )
        assert verdict.action == VerdictAction.ACCEPT
        assert verdict.contradictions == ()
        assert verdict.cost_tokens == 0

    def test_quarantine_verdict(self):
        verdict = BeliefVerdict(
            action=VerdictAction.QUARANTINE,
            model="opus",
            contradictions=("b-1", "b-2"),
            reason="Belief contradicts axiomatic B-1 and B-2",
        )
        assert verdict.action == VerdictAction.QUARANTINE
        assert len(verdict.contradictions) == 2

    def test_frozen(self):
        verdict = BeliefVerdict(action=VerdictAction.SKIP, model="infra")
        with pytest.raises(FrozenInstanceError):
            verdict.action = VerdictAction.ACCEPT  # type: ignore[misc]
