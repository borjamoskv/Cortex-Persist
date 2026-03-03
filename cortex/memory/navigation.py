"""CORTEX v8 — Semantic Navigation Protocol (SNP).

Vectorial GPS for concept traversal through semantic space.
Translates hippocampal place cells and grid cells into a navigable
topological index over embeddings.

Components:
  - AnchorEmbedding: Stable vector points representing "places" in concept space
  - TopologicalIndex: Hex-grid inspired neighbor structure for balanced exploration
  - SemanticNavigator: A* pathfinding through the anchor graph

Biological basis:
  - Place Cells → Anchor Embeddings (fire at specific "locations" in concept space)
  - Grid Cells → Topological Coordinate Index (metric relationships between anchors)
  - Hippocampal pathfinding → A* with semantic distance heuristic

Derivation: Ω₁ (Multi-Scale Causality) + Ω₄ (Aesthetic Integrity)
  → Navigate between concepts at the right scale. Ugly paths = wrong paths.
"""

from __future__ import annotations

import heapq
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Final

logger = logging.getLogger("cortex.memory.navigation")

__all__ = ["AnchorEmbedding", "SemanticNavigator", "TopologicalIndex"]

# ─── Constants ────────────────────────────────────────────────────────

# Activation threshold: anchor fires when query similarity exceeds this
ANCHOR_ACTIVATION_THRESHOLD: Final[float] = 0.85

# Maximum hex-neighbors per anchor (inspired by grid cell hexagonal tiling)
MAX_HEX_NEIGHBORS: Final[int] = 6

# Default max hops for pathfinding
DEFAULT_MAX_HOPS: Final[int] = 5

# Minimum edge weight to keep (prune weaker connections)
MIN_EDGE_WEIGHT: Final[float] = 0.1


# ─── Data Models ──────────────────────────────────────────────────────


@dataclass(slots=True)
class AnchorEmbedding:
    """Stable vector point representing a 'place' in concept space.

    Anchors are persistent landmarks that activate when a query falls
    within their receptive field (cosine similarity > threshold).

    Attributes:
        anchor_id: Unique identifier (e.g., project name or concept label).
        label: Human-readable label for display.
        embedding: Dense vector representation.
        co_activation_count: How often this anchor has been activated.
        last_activated: Unix timestamp of last activation.
        metadata: Arbitrary structured metadata.
    """

    anchor_id: str
    label: str
    embedding: list[float]
    co_activation_count: int = 0
    last_activated: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def activate(self) -> None:
        """Record an activation event."""
        self.co_activation_count += 1
        self.last_activated = time.time()

    @property
    def age_hours(self) -> float:
        """Hours since last activation."""
        return max(0.0, (time.time() - self.last_activated) / 3600.0)


@dataclass(slots=True, frozen=True)
class NavigationStep:
    """Single step in a semantic navigation path."""

    anchor_id: str
    label: str
    similarity: float
    cumulative_distance: float


@dataclass(slots=True)
class NavigationResult:
    """Result of a semantic navigation query."""

    path: list[NavigationStep] = field(default_factory=list)
    total_distance: float = 0.0
    hops: int = 0
    found: bool = False
    duration_ms: float = 0.0

    @property
    def confidence(self) -> float:
        """Overall navigation confidence based on path quality."""
        if not self.path:
            return 0.0
        avg_sim = sum(s.similarity for s in self.path) / len(self.path)
        # Penalize long paths
        hop_penalty = max(0.0, 1.0 - (self.hops / (DEFAULT_MAX_HOPS * 2)))
        return avg_sim * hop_penalty


# ─── Core Functions ───────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """O(d) cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_distance(a: list[float], b: list[float]) -> float:
    """Convert cosine similarity to a distance metric for A* search.

    Returns 1 - cosine_similarity, so 0.0 = identical, 1.0 = orthogonal.
    """
    return 1.0 - _cosine_similarity(a, b)


# ─── Topological Index ───────────────────────────────────────────────


class TopologicalIndex:
    """Hex-grid inspired neighbor structure for anchor embeddings.

    Each anchor maintains up to MAX_HEX_NEIGHBORS nearest neighbors,
    creating a navigable mesh. Edges are weighted by co-activation
    frequency (Hebbian) and semantic similarity.

    The hex structure balances exploration (broad neighbors) with
    exploitation (strong, frequent neighbors).
    """

    __slots__ = ("_anchors", "_edges")

    def __init__(self) -> None:
        # anchor_id → AnchorEmbedding
        self._anchors: dict[str, AnchorEmbedding] = {}
        # anchor_id → {neighbor_id: edge_weight}
        self._edges: dict[str, dict[str, float]] = {}

    def add_anchor(self, anchor: AnchorEmbedding) -> None:
        """Register a new anchor and compute its hex-neighbors."""
        self._anchors[anchor.anchor_id] = anchor
        if anchor.anchor_id not in self._edges:
            self._edges[anchor.anchor_id] = {}

        # Compute distances to all existing anchors and keep top-K
        distances: list[tuple[str, float]] = []
        for aid, existing in self._anchors.items():
            if aid == anchor.anchor_id:
                continue
            sim = _cosine_similarity(anchor.embedding, existing.embedding)
            if sim >= MIN_EDGE_WEIGHT:
                distances.append((aid, sim))

        # Sort by similarity (highest first) and keep MAX_HEX_NEIGHBORS
        distances.sort(key=lambda x: x[1], reverse=True)

        for neighbor_id, sim in distances[:MAX_HEX_NEIGHBORS]:
            self._edges[anchor.anchor_id][neighbor_id] = sim
            # Bidirectional — ensure neighbor also links back
            if neighbor_id not in self._edges:
                self._edges[neighbor_id] = {}
            # Only add if neighbor has room or this connection is stronger
            neighbor_edges = self._edges[neighbor_id]
            if len(neighbor_edges) < MAX_HEX_NEIGHBORS:
                neighbor_edges[anchor.anchor_id] = sim
            else:
                # Replace weakest if this is stronger
                weakest_id = min(neighbor_edges, key=neighbor_edges.get)  # type: ignore[arg-type]
                if sim > neighbor_edges[weakest_id]:
                    del neighbor_edges[weakest_id]
                    neighbor_edges[anchor.anchor_id] = sim

    def remove_anchor(self, anchor_id: str) -> None:
        """Remove an anchor and clean up edges."""
        self._anchors.pop(anchor_id, None)
        self._edges.pop(anchor_id, None)
        # Remove from neighbors
        for edges in self._edges.values():
            edges.pop(anchor_id, None)

    def get_anchor(self, anchor_id: str) -> AnchorEmbedding | None:
        return self._anchors.get(anchor_id)

    def get_neighbors(self, anchor_id: str) -> list[tuple[str, float]]:
        """Return neighbors sorted by edge weight (descending)."""
        edges = self._edges.get(anchor_id, {})
        return sorted(edges.items(), key=lambda x: x[1], reverse=True)

    def find_closest_anchor(
        self,
        embedding: list[float],
        threshold: float = ANCHOR_ACTIVATION_THRESHOLD,
    ) -> AnchorEmbedding | None:
        """Find the anchor closest to a query embedding.

        Returns None if no anchor exceeds the activation threshold.
        """
        best_anchor: AnchorEmbedding | None = None
        best_sim = 0.0

        for anchor in self._anchors.values():
            sim = _cosine_similarity(embedding, anchor.embedding)
            if sim > best_sim:
                best_sim = sim
                best_anchor = anchor

        if best_anchor and best_sim >= threshold:
            best_anchor.activate()
            return best_anchor
        return None

    def strengthen_edge(self, a_id: str, b_id: str, boost: float = 0.1) -> None:
        """Strengthen the edge between two anchors (Hebbian LTP)."""
        if a_id in self._edges and b_id in self._edges.get(a_id, {}):
            self._edges[a_id][b_id] = min(1.0, self._edges[a_id][b_id] + boost)
        if b_id in self._edges and a_id in self._edges.get(b_id, {}):
            self._edges[b_id][a_id] = min(1.0, self._edges[b_id][a_id] + boost)

    @property
    def anchor_count(self) -> int:
        return len(self._anchors)

    @property
    def edge_count(self) -> int:
        return sum(len(e) for e in self._edges.values()) // 2  # bidirectional


# ─── Semantic Navigator ──────────────────────────────────────────────


class SemanticNavigator:
    """A* pathfinding through semantic space.

    Finds multi-hop paths between concepts using the topological index.
    The heuristic is semantic distance to the target, admissible because
    cosine distance satisfies the triangle inequality in normalized space.

    Usage:
        index = TopologicalIndex()
        index.add_anchor(AnchorEmbedding("python", "Python", [0.8, 0.1, ...]))
        index.add_anchor(AnchorEmbedding("ml", "Machine Learning", [0.7, 0.3, ...]))
        index.add_anchor(AnchorEmbedding("tf", "TensorFlow", [0.6, 0.5, ...]))

        nav = SemanticNavigator(index)
        result = nav.navigate(query_embedding=[0.8, 0.1, ...], target_id="tf")
    """

    __slots__ = ("_index",)

    def __init__(self, index: TopologicalIndex) -> None:
        self._index = index

    def navigate(
        self,
        query_embedding: list[float],
        target_id: str,
        *,
        max_hops: int = DEFAULT_MAX_HOPS,
        activation_threshold: float = ANCHOR_ACTIVATION_THRESHOLD,
    ) -> NavigationResult:
        """Find a path from a query embedding to a target concept.

        Uses A* search with semantic distance as the heuristic function.

        Args:
            query_embedding: Starting point in vector space.
            target_id: Anchor ID of the destination concept.
            max_hops: Maximum path length.
            activation_threshold: Minimum similarity to activate start anchor.

        Returns:
            NavigationResult with ordered path, confidence, and timing.
        """
        start_time = time.monotonic()
        result = NavigationResult()

        # Find starting anchor
        start_anchor = self._index.find_closest_anchor(
            query_embedding, threshold=activation_threshold
        )
        if start_anchor is None:
            logger.debug(
                "SNP: No anchor activated for query (threshold=%.2f)", activation_threshold
            )
            result.duration_ms = (time.monotonic() - start_time) * 1000
            return result

        # Verify target exists
        target_anchor = self._index.get_anchor(target_id)
        if target_anchor is None:
            logger.debug("SNP: Target anchor '%s' not found", target_id)
            result.duration_ms = (time.monotonic() - start_time) * 1000
            return result

        # Early exit: start IS the target
        if start_anchor.anchor_id == target_id:
            result.path = [
                NavigationStep(
                    anchor_id=target_id,
                    label=target_anchor.label,
                    similarity=1.0,
                    cumulative_distance=0.0,
                )
            ]
            result.found = True
            result.hops = 0
            result.duration_ms = (time.monotonic() - start_time) * 1000
            return result

        # A* Search
        path = self._astar(start_anchor, target_anchor, max_hops)

        if path:
            result.path = path
            result.found = True
            result.hops = len(path) - 1
            result.total_distance = path[-1].cumulative_distance if path else 0.0

            # Strengthen edges along the path (Hebbian reinforcement)
            for i in range(len(path) - 1):
                self._index.strengthen_edge(path[i].anchor_id, path[i + 1].anchor_id)

        result.duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "SNP navigate: %s → %s | found=%s, hops=%d, confidence=%.3f, %.1fms",
            start_anchor.label,
            target_anchor.label,
            result.found,
            result.hops,
            result.confidence,
            result.duration_ms,
        )

        return result

    def _astar(
        self,
        start: AnchorEmbedding,
        target: AnchorEmbedding,
        max_hops: int,
    ) -> list[NavigationStep]:
        """A* search through the topological index.

        Heuristic: semantic distance to target (admissible in normalized space).
        """
        target_emb = target.embedding

        # Priority queue: (f_score, counter, anchor_id)
        counter = 0
        open_set: list[tuple[float, int, str]] = []
        start_h = _semantic_distance(start.embedding, target_emb)
        heapq.heappush(open_set, (start_h, counter, start.anchor_id))

        # Tracking
        came_from: dict[str, str] = {}
        g_score: dict[str, float] = {start.anchor_id: 0.0}
        depths: dict[str, int] = {start.anchor_id: 0}

        while open_set:
            _, _, current_id = heapq.heappop(open_set)

            # Goal reached
            if current_id == target.anchor_id:
                return self._reconstruct_path(came_from, current_id, g_score)

            current_depth = depths.get(current_id, 0)
            if current_depth >= max_hops:
                continue

            current_anchor = self._index.get_anchor(current_id)
            if current_anchor is None:
                continue

            for neighbor_id, edge_weight in self._index.get_neighbors(current_id):
                neighbor_anchor = self._index.get_anchor(neighbor_id)
                if neighbor_anchor is None:
                    continue

                # Cost: inverse of edge weight (strong edges = low cost)
                move_cost = 1.0 - edge_weight
                tentative_g = g_score.get(current_id, float("inf")) + move_cost

                if tentative_g < g_score.get(neighbor_id, float("inf")):
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g
                    depths[neighbor_id] = current_depth + 1

                    h = _semantic_distance(neighbor_anchor.embedding, target_emb)
                    f = tentative_g + h
                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbor_id))

        # No path found
        return []

    def _reconstruct_path(
        self,
        came_from: dict[str, str],
        current_id: str,
        g_score: dict[str, float],
    ) -> list[NavigationStep]:
        """Reconstruct the path from A* came_from map."""
        path_ids: list[str] = [current_id]
        while current_id in came_from:
            current_id = came_from[current_id]
            path_ids.append(current_id)
        path_ids.reverse()

        steps: list[NavigationStep] = []
        for i, aid in enumerate(path_ids):
            anchor = self._index.get_anchor(aid)
            if anchor is None:
                continue
            # Similarity to next step (or 1.0 for target)
            if i < len(path_ids) - 1:
                next_anchor = self._index.get_anchor(path_ids[i + 1])
                sim = _cosine_similarity(
                    anchor.embedding,
                    next_anchor.embedding if next_anchor else [],
                )
            else:
                sim = 1.0
            steps.append(
                NavigationStep(
                    anchor_id=aid,
                    label=anchor.label,
                    similarity=round(sim, 4),
                    cumulative_distance=round(g_score.get(aid, 0.0), 4),
                )
            )
        return steps
