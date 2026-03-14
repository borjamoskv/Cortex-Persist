"""Tests for merge.py — CRDT merge per belief type."""

from __future__ import annotations

import pytest

from benchmarks.encb.belief_object import (
    BeliefObject,
    BeliefType,
    Evidence,
)
from benchmarks.encb.merge import (
    merge_boolean,
    merge_categorical,
    merge_scalar,
    merge_set,
    merge_version_vectors,
)


class TestMergeVersionVectors:
    """Test version vector merging."""

    def test_merge_disjoint(self):
        result = merge_version_vectors({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_overlapping_takes_max(self):
        result = merge_version_vectors({"a": 3, "b": 1}, {"a": 1, "b": 5})
        assert result == {"a": 3, "b": 5}

    def test_merge_empty(self):
        result = merge_version_vectors({}, {"a": 1})
        assert result == {"a": 1}


class TestMergeBoolean:
    """Test boolean CRDT merge."""

    def test_dominating_wins(self):
        local = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 2, 0.9)
        local.version_vector = {"a": 2}

        remote = BeliefObject.new("k", BeliefType.BOOLEAN, False, "a", 1, 0.7)
        remote.version_vector = {"a": 1}

        result = merge_boolean(local, remote)
        assert result.value is True
        assert result.version_vector["a"] == 2

    def test_concurrent_higher_confidence_wins(self):
        local = BeliefObject.new("k", BeliefType.BOOLEAN, True, "a", 1, 0.6)
        local.version_vector = {"a": 2, "b": 1}

        remote = BeliefObject.new("k", BeliefType.BOOLEAN, False, "b", 2, 0.9)
        remote.version_vector = {"a": 1, "b": 3}

        result = merge_boolean(local, remote)
        assert result.value is False  # higher confidence wins
        assert result.confidence == 0.9


class TestMergeCategorical:
    """Test categorical CRDT merge."""

    def test_dominating_wins(self):
        local = BeliefObject.new("k", BeliefType.CATEGORICAL, "python", "a", 3, 0.8)
        local.version_vector = {"a": 3}

        remote = BeliefObject.new("k", BeliefType.CATEGORICAL, "go", "a", 1, 0.5)
        remote.version_vector = {"a": 1}

        result = merge_categorical(local, remote)
        assert result.value == "python"


class TestMergeScalar:
    """Test scalar CRDT merge."""

    def test_dominating_wins(self):
        local = BeliefObject.new("k", BeliefType.SCALAR, 100.0, "a", 5, 0.85)
        local.version_vector = {"a": 5}

        remote = BeliefObject.new("k", BeliefType.SCALAR, 200.0, "a", 2, 0.6)
        remote.version_vector = {"a": 2}

        result = merge_scalar(local, remote)
        # local dominates, but merge_scalar uses evidence-based median
        # Since local has more recent evidence, value should be close to 100.0
        assert result.version_vector["a"] == 5

    def test_concurrent_merges_evidence(self):
        local = BeliefObject.new("k", BeliefType.SCALAR, 100.0, "a", 1, 0.8)
        local.version_vector = {"a": 2, "b": 1}

        remote = BeliefObject.new("k", BeliefType.SCALAR, 200.0, "b", 2, 0.8)
        remote.version_vector = {"a": 1, "b": 2}

        result = merge_scalar(local, remote)
        # Both have equal confidence, evidence list is merged
        assert result.version_vector == {"a": 2, "b": 2}


class TestMergeSet:
    """Test set CRDT merge."""

    def test_union_on_merge(self):
        local = BeliefObject.new("k", BeliefType.SET, {"a", "b"}, "n1", 1, 0.7)
        local.version_vector = {"n1": 1}

        remote = BeliefObject.new("k", BeliefType.SET, {"b", "c"}, "n2", 1, 0.7)
        remote.version_vector = {"n2": 1}

        result = merge_set(local, remote)
        assert result.value == {"a", "b", "c"}
