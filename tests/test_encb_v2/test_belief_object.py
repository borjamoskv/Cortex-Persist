"""Tests for belief_object.py — BeliefObject, Evidence, version vectors."""

from __future__ import annotations

import pytest

from benchmarks.encb.belief_object import (
    BeliefObject,
    BeliefType,
    Evidence,
)


class TestBeliefObjectNew:
    """Test factory method."""

    def test_boolean_belief(self):
        b = BeliefObject.new("test.enabled", BeliefType.BOOLEAN, True, "n0", 1, 0.9)
        assert b.proposition_key == "test.enabled"
        assert b.belief_type == BeliefType.BOOLEAN
        assert b.value is True
        assert b.confidence == 0.9
        assert b.version_vector == {"n0": 1}
        assert len(b.evidences) == 1

    def test_categorical_belief(self):
        b = BeliefObject.new("test.lang", BeliefType.CATEGORICAL, "python", "n0", 1, 0.8)
        assert b.value == "python"

    def test_scalar_belief(self):
        b = BeliefObject.new("test.timeout", BeliefType.SCALAR, 250.0, "n0", 1, 0.7)
        assert b.value == 250.0

    def test_set_belief(self):
        b = BeliefObject.new("test.tools", BeliefType.SET, {"web", "file"}, "n0", 1, 0.6)
        assert b.value == {"web", "file"}

    def test_confidence_clamped(self):
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "n0", 1, 1.5)
        assert b.confidence == 1.0
        b2 = BeliefObject.new("k", BeliefType.BOOLEAN, True, "n0", 1, -0.5)
        assert b2.confidence == 0.0


class TestVersionVector:
    """Test CRDT version vector operations."""

    def test_dominates_true(self):
        a = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.5)
        a.version_vector = {"a": 3, "b": 2}
        b = BeliefObject.new("k", BeliefType.BOOLEAN, False, "b", 1, 0.5)
        b.version_vector = {"a": 2, "b": 1}
        assert a.dominates(b)

    def test_dominates_false_equal(self):
        a = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.5)
        a.version_vector = {"a": 3, "b": 2}
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "b", 1, 0.5)
        b.version_vector = {"a": 3, "b": 2}
        assert not a.dominates(b)

    def test_dominates_false_lesser(self):
        a = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.5)
        a.version_vector = {"a": 1}
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "b", 1, 0.5)
        b.version_vector = {"a": 2}
        assert not a.dominates(b)

    def test_concurrent_with(self):
        a = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.5)
        a.version_vector = {"a": 3, "b": 1}
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "b", 1, 0.5)
        b.version_vector = {"a": 1, "b": 3}
        assert a.concurrent_with(b)

    def test_not_concurrent_when_dominating(self):
        a = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.5)
        a.version_vector = {"a": 3, "b": 2}
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "b", 1, 0.5)
        b.version_vector = {"a": 2, "b": 1}
        assert not a.concurrent_with(b)


class TestEvidence:
    """Test Evidence dataclass."""

    def test_evidence_make(self):
        e = Evidence.make("agent:test", 1000, 0.85, "k", True)
        assert e.source_node == "agent:test"
        assert e.confidence == 0.85
        assert e.timestamp == 1000

    def test_add_evidence(self):
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "n0", 1, 0.5)
        e = Evidence.make("n1", 2, 0.9, "k", True)
        b.add_evidence(e, "n1")
        assert len(b.evidences) == 2
        assert b.version_vector["n1"] == 1


class TestBeliefObjectMiscellaneous:
    """Edge cases and general properties."""

    def test_unique_ids(self):
        b1 = BeliefObject.new("k1", BeliefType.BOOLEAN, True, "n0", 1, 0.5)
        b2 = BeliefObject.new("k2", BeliefType.BOOLEAN, False, "n0", 1, 0.5)
        assert b1.belief_id != b2.belief_id

    def test_mutable_value(self):
        b = BeliefObject.new("k", BeliefType.SCALAR, 10.0, "n0", 1, 0.5)
        b.value = 20.0
        assert b.value == 20.0

    def test_set_value_mutable(self):
        b = BeliefObject.new("k", BeliefType.SET, {"a", "b"}, "n0", 1, 0.5)
        b.value.add("c")
        assert "c" in b.value

    def test_latest_timestamp(self):
        b = BeliefObject.new("k", BeliefType.BOOLEAN, True, "n0", 5, 0.5)
        assert b.latest_timestamp == 5
        e = Evidence.make("n1", 10, 0.8, "k", True)
        b.add_evidence(e, "n1")
        assert b.latest_timestamp == 10
