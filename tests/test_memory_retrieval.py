"""Tests for cortex.memory.memory_retrieval — RRF fusion, fact_to_dict, Hebbian boost.

Pure function tests — no DB, no LLM, no async.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────


@dataclass
class FakeFact:
    """Minimal CortexFactModel stand-in for testing pure functions."""

    id: str
    content: str = "test content"
    timestamp: float = 1710000000.0
    metadata: dict[str, Any] = field(default_factory=dict)
    _recall_score: float = 0.0


# ─── fact_to_dict ────────────────────────────────────────────────────────


class TestFactToDict:
    """Tests for the fact_to_dict serializer."""

    def test_basic_serialization(self):
        from cortex.memory.memory_retrieval import fact_to_dict

        fact = FakeFact(id="f1", content="hello", timestamp=1.0, metadata={"k": "v"})
        d = fact_to_dict(fact)
        assert d["id"] == "f1"
        assert d["content"] == "hello"
        assert d["timestamp"] == 1.0
        assert d["metadata"] == {"k": "v"}

    def test_explicit_rrf_score(self):
        from cortex.memory.memory_retrieval import fact_to_dict

        fact = FakeFact(id="f1")
        d = fact_to_dict(fact, rrf_score=0.42)
        assert d["score"] == 0.42

    def test_fallback_to_recall_score(self):
        from cortex.memory.memory_retrieval import fact_to_dict

        fact = FakeFact(id="f1", _recall_score=0.99)
        d = fact_to_dict(fact)
        assert d["score"] == 0.99


# ─── apply_rrf ───────────────────────────────────────────────────────────


class TestApplyRRF:
    """Tests for Reciprocal Rank Fusion."""

    def test_empty_lists_return_empty(self):
        from cortex.memory.memory_retrieval import apply_rrf

        assert apply_rrf([], []) == []

    def test_single_source_dense_only(self):
        from cortex.memory.memory_retrieval import apply_rrf

        dense = [FakeFact(id="a"), FakeFact(id="b")]
        result = apply_rrf(dense, [], limit=5)
        assert len(result) == 2
        assert result[0]["id"] == "a"  # rank 0 → higher RRF

    def test_single_source_hdc_only(self):
        from cortex.memory.memory_retrieval import apply_rrf

        hdc = [FakeFact(id="x"), FakeFact(id="y")]
        result = apply_rrf([], hdc, limit=5)
        assert len(result) == 2
        assert result[0]["id"] == "x"

    def test_overlap_boosts_score(self):
        from cortex.memory.memory_retrieval import apply_rrf

        shared = FakeFact(id="shared")
        dense_only = FakeFact(id="dense_only")

        # shared appears in both lists → higher combined RRF
        dense = [shared, dense_only]
        hdc = [shared]

        result = apply_rrf(dense, hdc, limit=5, k=60)
        assert result[0]["id"] == "shared"
        assert result[0]["score"] > result[1]["score"]

    def test_limit_respected(self):
        from cortex.memory.memory_retrieval import apply_rrf

        facts = [FakeFact(id=f"f{i}") for i in range(10)]
        result = apply_rrf(facts, [], limit=3)
        assert len(result) == 3

    def test_rrf_scores_decrease_with_rank(self):
        from cortex.memory.memory_retrieval import apply_rrf

        facts = [FakeFact(id=f"f{i}") for i in range(5)]
        result = apply_rrf(facts, [], limit=5, k=60)
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)


# ─── _apply_hebbian_boost ────────────────────────────────────────────────


class TestHebbianBoost:
    """Tests for STDP Hebbian ranking boost."""

    def test_no_stdp_engine_passthrough(self):
        from cortex.memory.memory_retrieval import _apply_hebbian_boost
        from unittest.mock import MagicMock

        manager = MagicMock(spec=[])
        results = [{"id": "a", "score": 1.0}, {"id": "b", "score": 0.5}]
        boosted = _apply_hebbian_boost(manager, results)
        assert boosted == results

    def test_single_result_passthrough(self):
        from cortex.memory.memory_retrieval import _apply_hebbian_boost
        from unittest.mock import MagicMock

        manager = MagicMock()
        manager._stdp_engine = MagicMock()
        results = [{"id": "a", "score": 1.0}]
        boosted = _apply_hebbian_boost(manager, results)
        assert boosted == results

    def test_strong_edge_boosts_score(self):
        from cortex.memory.memory_retrieval import _apply_hebbian_boost
        from unittest.mock import MagicMock

        manager = MagicMock()
        stdp = MagicMock()
        stdp.get_edge_weight.return_value = 5.0  # Strong co-activation
        manager._stdp_engine = stdp

        results = [
            {"id": "a", "score": 1.0},
            {"id": "b", "score": 0.5},
        ]
        boosted = _apply_hebbian_boost(manager, results)
        # Both should get Hebbian boost from each other
        assert boosted[0]["score"] > 1.0
        assert boosted[1]["score"] > 0.5
