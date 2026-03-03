"""Tests for CORTEX v8 — Associative Dream Engine (REM Phase)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.memory.dream import (
    AssociativeDreamEngine,
    DreamResult,
    SemanticCluster,
    SyntheticBridge,
    _compute_centroid,
    _cosine_similarity,
)


# ─── Helpers ──────────────────────────────────────────────────────────


def _mock_engram(
    eid: str,
    embedding: list[float],
    project_id: str = "test",
    energy: float = 0.8,
    entangled_refs: list[str] | None = None,
    timestamp: float = 0.0,
) -> MagicMock:
    """Create a mock engram with required attributes."""
    e = MagicMock()
    e.id = eid
    e.embedding = embedding
    e.project_id = project_id
    e.energy_level = energy
    e.entangled_refs = entangled_refs or []
    e.timestamp = timestamp
    e.metadata = {}
    e.content = f"Content of {eid}"
    return e


# ─── DreamResult Tests ───────────────────────────────────────────────


class TestDreamResult:
    def test_initial_state(self) -> None:
        result = DreamResult()
        assert result.total_operations == 0

    def test_total_operations(self) -> None:
        result = DreamResult(
            clusters_found=3,
            bridges_created=2,
            engrams_reweighted=5,
            redundant_nodes_fused=1,
        )
        assert result.total_operations == 11


# ─── Cluster Detection Tests ─────────────────────────────────────────


class TestClusterDetection:
    def test_similar_engrams_cluster(self) -> None:
        engine = AssociativeDreamEngine(cluster_threshold=0.8)
        engrams = [
            _mock_engram("a", [0.9, 0.1, 0.0]),
            _mock_engram("b", [0.85, 0.15, 0.0]),
            _mock_engram("c", [0.0, 0.0, 1.0]),  # Outlier
        ]
        clusters = engine._detect_clusters(engrams)
        assert len(clusters) >= 1
        # a and b should be in same cluster
        for cluster in clusters:
            if "a" in cluster.member_ids:
                assert "b" in cluster.member_ids

    def test_no_clusters_when_all_different(self) -> None:
        engine = AssociativeDreamEngine(cluster_threshold=0.99)
        engrams = [
            _mock_engram("a", [1.0, 0.0, 0.0]),
            _mock_engram("b", [0.0, 1.0, 0.0]),
            _mock_engram("c", [0.0, 0.0, 1.0]),
        ]
        clusters = engine._detect_clusters(engrams)
        assert len(clusters) == 0

    def test_cluster_has_centroid(self) -> None:
        engine = AssociativeDreamEngine(cluster_threshold=0.5)
        engrams = [
            _mock_engram("a", [1.0, 0.0]),
            _mock_engram("b", [0.8, 0.2]),
        ]
        clusters = engine._detect_clusters(engrams)
        if clusters:
            assert len(clusters[0].centroid) == 2

    def test_cluster_dominant_project(self) -> None:
        engine = AssociativeDreamEngine(cluster_threshold=0.5)
        engrams = [
            _mock_engram("a", [1.0, 0.0], project_id="CORTEX"),
            _mock_engram("b", [0.9, 0.1], project_id="CORTEX"),
        ]
        clusters = engine._detect_clusters(engrams)
        if clusters:
            assert clusters[0].dominant_project == "CORTEX"


# ─── Synthetic Bridging Tests ────────────────────────────────────────


class TestSyntheticBridging:
    def test_bridges_between_medium_distance_clusters(self) -> None:
        engine = AssociativeDreamEngine(
            bridge_min_distance=0.2,
            bridge_max_distance=0.8,
        )
        clusters = [
            SemanticCluster(
                cluster_id="c0",
                member_ids=["a"],
                centroid=[1.0, 0.0, 0.0],
                dominant_project="P1",
            ),
            SemanticCluster(
                cluster_id="c1",
                member_ids=["b"],
                centroid=[0.5, 0.5, 0.5],
                dominant_project="P2",
            ),
        ]
        bridges = engine._generate_bridges(clusters)
        assert len(bridges) >= 1
        assert bridges[0].source_cluster_id == "c0"
        assert bridges[0].target_cluster_id == "c1"

    def test_no_bridges_between_identical_clusters(self) -> None:
        engine = AssociativeDreamEngine(
            bridge_min_distance=0.3,
            bridge_max_distance=0.7,
        )
        clusters = [
            SemanticCluster(
                cluster_id="c0",
                member_ids=["a"],
                centroid=[1.0, 0.0],
                dominant_project="P1",
            ),
            SemanticCluster(
                cluster_id="c1",
                member_ids=["b"],
                centroid=[1.0, 0.0],
                dominant_project="P1",
            ),
        ]
        bridges = engine._generate_bridges(clusters)
        assert len(bridges) == 0  # Distance = 0 < bridge_min

    def test_bridge_hypothesis_contains_projects(self) -> None:
        engine = AssociativeDreamEngine(
            bridge_min_distance=0.1,
            bridge_max_distance=0.9,
        )
        clusters = [
            SemanticCluster(
                cluster_id="c0",
                member_ids=["a"],
                centroid=[1.0, 0.0],
                dominant_project="Python",
            ),
            SemanticCluster(
                cluster_id="c1",
                member_ids=["b"],
                centroid=[0.5, 0.5],
                dominant_project="Rust",
            ),
        ]
        bridges = engine._generate_bridges(clusters)
        if bridges:
            assert "Python" in bridges[0].bridge_hypothesis
            assert "Rust" in bridges[0].bridge_hypothesis


# ─── Full Dream Cycle Tests ──────────────────────────────────────────


class TestDreamCycle:
    @pytest.mark.asyncio
    async def test_dream_cycle_with_empty_input(self) -> None:
        engine = AssociativeDreamEngine()
        result = await engine.dream_cycle(tenant_id="test", engrams=[])
        assert result.total_operations == 0

    @pytest.mark.asyncio
    async def test_dream_cycle_with_engrams(self) -> None:
        engine = AssociativeDreamEngine(cluster_threshold=0.5)
        engrams = [
            _mock_engram("a", [0.9, 0.1, 0.0], entangled_refs=["b", "c", "d"]),
            _mock_engram("b", [0.85, 0.15, 0.0], entangled_refs=["a"]),
            _mock_engram("c", [0.0, 0.0, 1.0], energy=0.2, entangled_refs=[]),
        ]
        result = await engine.dream_cycle(tenant_id="test", engrams=engrams)
        assert result.duration_ms >= 0
        assert result.clusters_found >= 0

    @pytest.mark.asyncio
    async def test_emotional_reweight_boosts_connected(self) -> None:
        engine = AssociativeDreamEngine()
        well_connected = _mock_engram(
            "a", [1.0, 0.0], energy=0.8,
            entangled_refs=["b", "c", "d"],
        )
        result = await engine._emotional_reweight([well_connected])
        assert result >= 1
        assert well_connected.metadata.get("dream_valence", 0) > 0

    @pytest.mark.asyncio
    async def test_emotional_reweight_dampens_isolated(self) -> None:
        engine = AssociativeDreamEngine()
        isolated = _mock_engram(
            "a", [1.0, 0.0], energy=0.1,
            entangled_refs=[],
        )
        result = await engine._emotional_reweight([isolated])
        assert result >= 1
        assert isolated.metadata.get("dream_valence", 0) < 0

    @pytest.mark.asyncio
    async def test_redundancy_fusion(self) -> None:
        mock_vs = AsyncMock()
        engine = AssociativeDreamEngine(vector_store=mock_vs)

        # Two near-identical engrams
        engrams = [
            _mock_engram("old", [1.0, 0.0, 0.0], timestamp=100),
            _mock_engram("new", [1.0, 0.0, 0.0], timestamp=200),
        ]
        clusters = [
            SemanticCluster(
                cluster_id="c0",
                member_ids=["old", "new"],
                centroid=[1.0, 0.0, 0.0],
            )
        ]
        fused = await engine._fuse_redundant(clusters, engrams)
        assert fused == 1
        mock_vs.delete.assert_called_once_with("old")  # Older one deleted


# ─── Utility Tests ────────────────────────────────────────────────────


class TestDreamUtils:
    def test_compute_centroid(self) -> None:
        c = _compute_centroid([[1.0, 0.0], [0.0, 1.0]])
        assert c == pytest.approx([0.5, 0.5])

    def test_compute_centroid_empty(self) -> None:
        assert _compute_centroid([]) == []

    def test_cosine_identical(self) -> None:
        assert _cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
