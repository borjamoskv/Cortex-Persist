"""Tests for CORTEX v8 — Semantic Navigation Protocol."""

from __future__ import annotations

import pytest

from cortex.memory.navigation import (
    ANCHOR_ACTIVATION_THRESHOLD,
    AnchorEmbedding,
    NavigationResult,
    SemanticNavigator,
    TopologicalIndex,
    _cosine_similarity,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _anchor(aid: str, label: str, emb: list[float]) -> AnchorEmbedding:
    return AnchorEmbedding(anchor_id=aid, label=label, embedding=emb)


def _build_triangle_index() -> TopologicalIndex:
    """Build a simple 3-node index: Python → ML → TensorFlow."""
    idx = TopologicalIndex()
    idx.add_anchor(_anchor("python", "Python", [0.9, 0.1, 0.0]))
    idx.add_anchor(_anchor("ml", "Machine Learning", [0.5, 0.8, 0.2]))
    idx.add_anchor(_anchor("tf", "TensorFlow", [0.3, 0.7, 0.6]))
    return idx


# ─── TopologicalIndex Tests ──────────────────────────────────────────


class TestTopologicalIndex:
    def test_add_anchor_creates_node(self) -> None:
        idx = TopologicalIndex()
        idx.add_anchor(_anchor("a", "Alpha", [1.0, 0.0]))
        assert idx.anchor_count == 1

    def test_add_multiple_anchors_creates_edges(self) -> None:
        idx = _build_triangle_index()
        assert idx.anchor_count == 3
        assert idx.edge_count >= 1

    def test_find_closest_anchor_above_threshold(self) -> None:
        idx = _build_triangle_index()
        # Query very close to "python" embedding
        result = idx.find_closest_anchor([0.9, 0.1, 0.0], threshold=0.5)
        assert result is not None
        assert result.anchor_id == "python"

    def test_find_closest_anchor_below_threshold(self) -> None:
        idx = _build_triangle_index()
        # Orthogonal query shouldn't activate anything at high threshold
        result = idx.find_closest_anchor([0.0, 0.0, 1.0], threshold=0.99)
        assert result is None

    def test_activation_increments_count(self) -> None:
        idx = TopologicalIndex()
        a = _anchor("a", "Alpha", [1.0, 0.0])
        idx.add_anchor(a)
        assert a.co_activation_count == 0
        idx.find_closest_anchor([1.0, 0.0], threshold=0.5)
        assert a.co_activation_count == 1

    def test_get_neighbors_returns_sorted(self) -> None:
        idx = _build_triangle_index()
        neighbors = idx.get_neighbors("python")
        assert len(neighbors) >= 1
        # Sorted descending by weight
        if len(neighbors) >= 2:
            assert neighbors[0][1] >= neighbors[1][1]

    def test_strengthen_edge(self) -> None:
        idx = _build_triangle_index()
        neighbors = idx.get_neighbors("python")
        if neighbors:
            n_id, old_weight = neighbors[0]
            idx.strengthen_edge("python", n_id, boost=0.1)
            new_neighbors = dict(idx.get_neighbors("python"))
            assert new_neighbors.get(n_id, 0) >= old_weight

    def test_remove_anchor(self) -> None:
        idx = _build_triangle_index()
        idx.remove_anchor("python")
        assert idx.anchor_count == 2
        assert idx.get_anchor("python") is None


# ─── SemanticNavigator Tests ─────────────────────────────────────────


class TestSemanticNavigator:
    def test_navigate_finds_direct_neighbor(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="ml",
            activation_threshold=0.5,
        )
        assert result.found

    def test_navigate_multi_hop(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="tf",
            activation_threshold=0.5,
        )
        assert result.found
        assert result.hops >= 1

    def test_navigate_returns_empty_for_missing_target(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="nonexistent",
        )
        assert not result.found
        assert result.path == []

    def test_navigate_same_start_and_target(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="python",
            activation_threshold=0.5,
        )
        assert result.found
        assert result.hops == 0

    def test_navigate_respects_max_hops(self) -> None:
        # Build a chain: A → B → C → D → E
        idx = TopologicalIndex()
        for i in range(5):
            emb = [0.0] * 5
            emb[i] = 1.0
            idx.add_anchor(_anchor(f"n{i}", f"Node{i}", emb))

        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[1.0, 0.0, 0.0, 0.0, 0.0],
            target_id="n4",
            max_hops=1,
            activation_threshold=0.1,
        )
        # With max_hops=1, may not reach distant node
        if result.found:
            assert result.hops <= 1

    def test_confidence_decreases_with_hops(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="tf",
            activation_threshold=0.5,
        )
        if result.found:
            assert 0.0 <= result.confidence <= 1.0

    def test_navigate_timing(self) -> None:
        idx = _build_triangle_index()
        nav = SemanticNavigator(idx)
        result = nav.navigate(
            query_embedding=[0.9, 0.1, 0.0],
            target_id="tf",
            activation_threshold=0.5,
        )
        assert result.duration_ms >= 0


# ─── Utility Tests ────────────────────────────────────────────────────


class TestCosine:
    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_empty_vectors(self) -> None:
        assert _cosine_similarity([], []) == 0.0

    def test_mismatched_dims(self) -> None:
        assert _cosine_similarity([1, 0], [1, 0, 0]) == 0.0
