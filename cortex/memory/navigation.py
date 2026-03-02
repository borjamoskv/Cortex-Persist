from __future__ import annotations

import heapq
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Final

logger = logging.getLogger("cortex.memory.navigation")

__all__ = ["AnchorEmbedding", "SemanticNavigator", "TopologicalIndex"]

ANCHOR_ACTIVATION_THRESHOLD: Final[float] = 0.85
MAX_HEX_NEIGHBORS: Final[int] = 6
DEFAULT_MAX_HOPS: Final[int] = 5
MIN_EDGE_WEIGHT: Final[float] = 0.1


@dataclass()
class AnchorEmbedding:
    anchor_id: str
    label: str
    embedding: list[float]
    co_activation_count: int = 0
    last_activated: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def activate(self) -> None:
        self.co_activation_count += 1
        self.last_activated = time.time()

    @property
    def age_hours(self) -> float:
        return max(0.0, (time.time() - self.last_activated) / 3600.0)


@dataclass(frozen=True)
class NavigationStep:
    anchor_id: str
    label: str
    similarity: float
    cumulative_distance: float


@dataclass()
class NavigationResult:
    path: list[NavigationStep] = field(default_factory=list)
    total_distance: float = 0.0
    hops: int = 0
    found: bool = False
    duration_ms: float = 0.0

    @property
    def confidence(self) -> float:
        if not self.path:
            return 0.0
        avg_sim = sum(s.similarity for s in self.path) / len(self.path)
        hop_penalty = max(0.0, 1.0 - (self.hops / (DEFAULT_MAX_HOPS * 2)))
        return avg_sim * hop_penalty


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_distance(a: list[float], b: list[float]) -> float:
    return 1.0 - _cosine_similarity(a, b)


class TopologicalIndex:
    __slots__ = ("_anchors", "_edges")

    def __init__(self) -> None:
        self._anchors: dict[str, AnchorEmbedding] = {}
        self._edges: dict[str, dict[str, float]] = {}

    def add_anchor(self, anchor: AnchorEmbedding) -> None:
        self._anchors[anchor.anchor_id] = anchor
        if anchor.anchor_id not in self._edges:
            self._edges[anchor.anchor_id] = {}

        distances = [
            (aid, sim)
            for aid, existing in self._anchors.items()
            if aid != anchor.anchor_id
            and (sim := _cosine_similarity(anchor.embedding, existing.embedding)) >= MIN_EDGE_WEIGHT
        ]

        distances.sort(key=lambda x: x[1], reverse=True)

        for neighbor_id, sim in distances[:MAX_HEX_NEIGHBORS]:
            self._edges[anchor.anchor_id][neighbor_id] = sim
            if neighbor_id not in self._edges:
                self._edges[neighbor_id] = {}
            neighbor_edges = self._edges[neighbor_id]
            if len(neighbor_edges) < MAX_HEX_NEIGHBORS:
                neighbor_edges[anchor.anchor_id] = sim
            else:
                weakest_id = min(neighbor_edges, key=neighbor_edges.get)
                if sim > neighbor_edges[weakest_id]:
                    del neighbor_edges[weakest_id]
                    neighbor_edges[anchor.anchor_id] = sim

    def remove_anchor(self, anchor_id: str) -> None:
        self._anchors.pop(anchor_id, None)
        self._edges.pop(anchor_id, None)
        for edges in self._edges.values():
            edges.pop(anchor_id, None)

    def get_anchor(self, anchor_id: str) -> AnchorEmbedding | None:
        return self._anchors.get(anchor_id)

    def get_neighbors(self, anchor_id: str) -> list[tuple[str, float]]:
        edges = self._edges.get(anchor_id, {})
        return sorted(edges.items(), key=lambda x: x[1], reverse=True)

    def find_closest_anchor(
        self, embedding: list[float], threshold: float = ANCHOR_ACTIVATION_THRESHOLD
    ) -> AnchorEmbedding | None:
        best_anchor = max(
            (
                (anchor, _cosine_similarity(embedding, anchor.embedding))
                for anchor in self._anchors.values()
            ),
            key=lambda x: x[1],
            default=(None, 0.0),
        )
        if best_anchor[0] and best_anchor[1] >= threshold:
            best_anchor[0].activate()
            return best_anchor[0]
        return None

    def strengthen_edge(self, a_id: str, b_id: str, boost: float = 0.1) -> None:
        if a_id in self._edges and b_id in self._edges.get(a_id, {}):
            self._edges[a_id][b_id] = min(1.0, self._edges[a_id][b_id] + boost)
        if b_id in self._edges and a_id in self._edges.get(b_id, {}):
            self._edges[b_id][a_id] = min(1.0, self._edges[b_id][a_id] + boost)

    @property
    def anchor_count(self) -> int:
        return len(self._anchors)

    @property
    def edge_count(self) -> int:
        return sum(len(e) for e in self._edges.values()) // 2


class SemanticNavigator:
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
        start_time = time.monotonic()
        result = NavigationResult()

        start_anchor = self._index.find_closest_anchor(
            query_embedding, threshold=activation_threshold
        )
        if start_anchor is None:
            logger.debug(
                "SNP: No anchor activated for query (threshold=%.2f)", activation_threshold
            )
            result.duration_ms = (time.monotonic() - start_time) * 1000
            return result

        target_anchor = self._index.get_anchor(target_id)
        if target_anchor is None:
            logger.debug("SNP: Target anchor '%s' not found", target_id)
            result.duration_ms = (time.monotonic() - start_time) * 1000
            return result

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

        path = self._astar(start_anchor, target_anchor, max_hops)

        if path:
            result.path = path
            result.found = True
            result.hops = len(path) - 1
            result.total_distance = path[-1].cumulative_distance if path else 0.0

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
        self, start: AnchorEmbedding, target: AnchorEmbedding, max_hops: int
    ) -> list[NavigationStep]:
        target_emb = target.embedding
        counter = 0
        open_set: list[tuple[float, int, str]] = []
        start_h = _semantic_distance(start.embedding, target_emb)
        heapq.heappush(open_set, (start_h, counter, start.anchor_id))

        came_from: dict[str, str] = {}
        g_score: dict[str, float] = {start.anchor_id: 0.0}
        depths: dict[str, int] = {start.anchor_id: 0}

        while open_set:
            _, _, current_id = heapq.heappop(open_set)

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

        return []

    def _reconstruct_path(
        self, came_from: dict[str, str], current_id: str, g_score: dict[str, float]
    ) -> list[NavigationStep]:
        path_ids = [current_id]
        while current_id in came_from:
            current_id = came_from[current_id]
            path_ids.append(current_id)
        path_ids.reverse()

        steps = []
        for i, aid in enumerate(path_ids):
            anchor = self._index.get_anchor(aid)
            if anchor is None:
                continue
            sim = (
                1.0
                if i == len(path_ids) - 1
                else _cosine_similarity(
                    anchor.embedding, self._index.get_anchor(path_ids[i + 1]).embedding
                )
            )
            steps.append(
                NavigationStep(
                    anchor_id=aid,
                    label=anchor.label,
                    similarity=round(sim, 4),
                    cumulative_distance=round(g_score.get(aid, 0.0), 4),
                )
            )
        return steps
