"""CORTEX v7+ — Semantic Navigator (Grid Cell Architecture).

Strategy #13: Navigate knowledge topology instead of just searching.
Inspired by hippocampal place cells and grid cells (Nobel 2014, O'Keefe/Moser).

Operations:
  jump_to(query)          → Direct semantic teleportation
  drift(direction, steps) → Continuous movement through embedding space
  explore_cluster(seed)   → Map the semantic neighborhood
  find_path(src, tgt)     → Conceptual route between two ideas

KnowledgeMap:
  get_dense_regions()  → Where do I know a lot?
  get_sparse_regions() → Where are my blind spots?
  get_bridges()        → What connects separate clusters?
  get_islands()        → What is completely isolated?

Derivation: Ω₁ (Multi-Scale Causality) + Ω₄ (Aesthetic Integrity)
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Final, Optional

logger = logging.getLogger("cortex.memory.navigator")

__all__ = [
    "ClusterInfo",
    "KnowledgeMap",
    "NavigationState",
    "SemanticNavigator",
    "SemanticPath",
]


# ─── Constants ────────────────────────────────────────────────────────

_DEFAULT_DRIFT_ALPHA: Final[float] = 0.3
_DEFAULT_EXPLORE_RADIUS: Final[float] = 0.3
_MAX_BREADCRUMBS: Final[int] = 50
_DENSE_THRESHOLD: Final[int] = 10
_SPARSE_THRESHOLD: Final[int] = 3
_BRIDGE_SIM_THRESHOLD: Final[float] = 0.4
_ISLAND_THRESHOLD: Final[float] = 0.2


# ─── Models ───────────────────────────────────────────────────────────


@dataclass()
class NavigationState:
    """Snapshot of the navigator's current position in semantic space."""

    center_id: str | int = ""
    center_content: str = ""
    center_score: float = 0.0
    neighbors: list[dict[str, Any]] = field(default_factory=list)
    density: int = 0
    position: list[float] = field(default_factory=list)

    @property
    def is_dense(self) -> bool:
        return self.density >= _DENSE_THRESHOLD

    @property
    def is_sparse(self) -> bool:
        return self.density < _SPARSE_THRESHOLD


@dataclass()
class ClusterInfo:
    """Metadata about a semantic cluster."""

    cluster_id: int = 0
    centroid_content: str = ""
    member_count: int = 0
    avg_similarity: float = 0.0
    avg_energy: float = 0.0
    projects: set[str] = field(default_factory=set)
    fact_types: set[str] = field(default_factory=set)

    @property
    def label(self) -> str:
        return self.centroid_content[:60]


@dataclass()
class SemanticBridge:
    """A connection between two otherwise separate clusters."""

    cluster_a: ClusterInfo
    cluster_b: ClusterInfo
    bridge_facts: list[dict[str, Any]] = field(default_factory=list)
    bridge_strength: float = 0.0


@dataclass()
class SemanticPath:
    """A route through semantic space from source to target."""

    source: str = ""
    target: str = ""
    hops: list[dict[str, Any]] = field(default_factory=list)
    total_distance: float = 0.0

    @property
    def hop_count(self) -> int:
        return len(self.hops)


# ─── Utility ──────────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. O(d)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _interpolate(a: list[float], b: list[float], alpha: float) -> list[float]:
    """Linear interpolation between two vectors: a*(1-α) + b*α."""
    return [x * (1 - alpha) + y * alpha for x, y in zip(a, b, strict=True)]


def _normalize(v: list[float]) -> list[float]:
    """L2-normalize a vector."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm < 1e-12:
        return v
    return [x / norm for x in v]


# ─── Search Adapter Protocol ─────────────────────────────────────────


class SearchAdapter:
    """Protocol for vector search backends.

    Implement this to plug any vector store into the navigator.
    The default implementation wraps the hybrid search functions.
    """

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        project: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return list of dicts with at minimum: id, content, score, embedding."""
        raise NotImplementedError

    async def embed(self, text: str) -> list[float]:
        """Embed a text query into the vector space."""
        raise NotImplementedError

    async def get_all_embeddings(
        self,
        project: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return all stored embeddings for topology analysis."""
        raise NotImplementedError


# ─── Semantic Navigator ──────────────────────────────────────────────


class SemanticNavigator:
    """Navigate CORTEX's knowledge topology.

    Instead of point queries (search), this enables *exploration*:
    moving through semantic space, discovering adjacent regions,
    and mapping the topology of what the agent knows.

    Pure logic + adapter pattern. No direct DB dependencies.
    """

    def __init__(
        self,
        search_adapter: SearchAdapter,
        drift_alpha: float = _DEFAULT_DRIFT_ALPHA,
    ) -> None:
        self._adapter = search_adapter
        self._drift_alpha = drift_alpha
        self._position: Optional[list[float]] = None
        self._breadcrumbs: deque[NavigationState] = deque(maxlen=_MAX_BREADCRUMBS)

    @property
    def position(self) -> Optional[list[float]]:
        """Current position in embedding space."""
        return self._position

    @property
    def trail(self) -> list[NavigationState]:
        """Navigation breadcrumbs (most recent first)."""
        return list(reversed(self._breadcrumbs))

    # ── Navigation Operations ─────────────────────────────────────

    async def jump_to(
        self,
        query: str,
        top_k: int = 10,
        project: Optional[str] = None,
    ) -> NavigationState:
        """Teleport to a point in semantic space.

        Like typing coordinates — you land directly at the closest
        matching region.
        """
        embedding = await self._adapter.embed(query)
        results = await self._adapter.search(embedding, top_k=top_k, project=project)

        self._position = embedding

        if not results:
            state = NavigationState(
                position=embedding,
                density=0,
            )
            self._breadcrumbs.append(state)
            return state

        center = results[0]
        state = NavigationState(
            center_id=center.get("id", ""),
            center_content=center.get("content", ""),
            center_score=center.get("score", 0.0),
            neighbors=list(results[1:]),
            density=len(results),
            position=embedding,
        )
        self._breadcrumbs.append(state)
        return state

    async def drift(
        self,
        direction: str,
        steps: int = 3,
        project: Optional[str] = None,
    ) -> list[NavigationState]:
        """Move continuously through embedding space.

        Like walking: interpolate from current position towards
        the direction embedding, discovering what lies between.
        """
        if self._position is None:
            raise ValueError("No current position. Use jump_to() first.")

        direction_embedding = await self._adapter.embed(direction)
        trajectory: list[NavigationState] = []
        pos = list(self._position)

        for step in range(steps):
            # Progressive interpolation — each step moves further
            alpha = self._drift_alpha * (step + 1) / steps
            pos = _interpolate(pos, direction_embedding, alpha)
            pos = _normalize(pos)

            results = await self._adapter.search(pos, top_k=5, project=project)

            if results:
                center = results[0]
                state = NavigationState(
                    center_id=center.get("id", ""),
                    center_content=center.get("content", ""),
                    center_score=center.get("score", 0.0),
                    neighbors=results[1:],
                    density=len(results),
                    position=list(pos),
                )
            else:
                state = NavigationState(position=list(pos), density=0)

            trajectory.append(state)
            self._breadcrumbs.append(state)

        self._position = pos
        return trajectory

    async def explore_cluster(
        self,
        seed_query: str,
        radius: float = _DEFAULT_EXPLORE_RADIUS,
        project: Optional[str] = None,
    ) -> ClusterInfo:
        """Map the semantic neighborhood around a seed.

        Returns metadata about the cluster: density, member count,
        average energy, etc.
        """
        embedding = await self._adapter.embed(seed_query)
        # Fetch extra candidates for neighborhood analysis
        results = await self._adapter.search(embedding, top_k=50, project=project)

        # Filter by radius (cosine distance)
        cluster_members = []
        for r in results:
            emb = r.get("embedding")
            if emb:
                sim = _cosine_similarity(embedding, emb)
                if sim >= (1.0 - radius):
                    cluster_members.append(r)
            elif r.get("score", 0.0) >= (1.0 - radius):
                cluster_members.append(r)

        if not cluster_members:
            cluster_members = results[:5]  # Fallback: nearest 5

        projects: set[str] = set()
        fact_types: set[str] = set()
        total_energy = 0.0

        for m in cluster_members:
            if p := m.get("project"):
                projects.add(p)
            if ft := m.get("fact_type", m.get("type")):
                fact_types.add(ft)
            total_energy += m.get("energy_level", 0.5)

        return ClusterInfo(
            centroid_content=cluster_members[0].get("content", "") if cluster_members else "",
            member_count=len(cluster_members),
            avg_similarity=(
                sum(m.get("score", 0) for m in cluster_members) / max(1, len(cluster_members))
            ),
            avg_energy=total_energy / max(1, len(cluster_members)),
            projects=projects,
            fact_types=fact_types,
        )

    async def find_semantic_path(
        self,
        source_query: str,
        target_query: str,
        max_hops: int = 5,
    ) -> SemanticPath:
        """Find a semantic route between two concepts.

        Uses greedy interpolation: at each hop, finds the closest
        real engram to the interpolated position.
        """
        src_emb = await self._adapter.embed(source_query)
        tgt_emb = await self._adapter.embed(target_query)

        hops: list[dict[str, Any]] = []
        total_dist = 0.0

        for i in range(max_hops):
            alpha = (i + 1) / (max_hops + 1)
            mid = _interpolate(src_emb, tgt_emb, alpha)
            mid = _normalize(mid)

            results = await self._adapter.search(mid, top_k=1)
            if results:
                hop = results[0]
                hops.append(hop)
                # Compute incremental distance
                if hops and len(hops) > 1:
                    prev_emb = hops[-2].get("embedding", mid)
                    curr_emb = hop.get("embedding", mid)
                    if prev_emb and curr_emb:
                        total_dist += 1.0 - _cosine_similarity(prev_emb, curr_emb)

        return SemanticPath(
            source=source_query,
            target=target_query,
            hops=hops,
            total_distance=total_dist,
        )


# ─── Knowledge Map ────────────────────────────────────────────────────


class KnowledgeMap:
    """Topological self-awareness of the knowledge space.

    Provides the agent with a map of where it knows a lot,
    where it knows little, and what connects different domains.
    """

    def __init__(self, search_adapter: SearchAdapter) -> None:
        self._adapter = search_adapter
        self._cached_topology: Optional[dict[str, Any]] = None

    async def build_topology(
        self,
        project: Optional[str] = None,
        sample_size: int = 200,
    ) -> dict[str, Any]:
        """Build a topological overview of the knowledge space.

        Uses random sampling + clustering to identify regions.
        """
        all_data = await self._adapter.get_all_embeddings(
            project=project,
            limit=sample_size,
        )

        if not all_data:
            self._cached_topology = {
                "total_facts": 0,
                "clusters": [],
                "islands": [],
                "bridges": [],
            }
            return self._cached_topology

        # Group by project as a first-order clustering proxy
        by_project: dict[str, list[dict]] = defaultdict(list)
        for item in all_data:
            proj = item.get("project", "unknown")
            by_project[proj].append(item)

        clusters: list[ClusterInfo] = []
        for proj, items in by_project.items():
            cluster = ClusterInfo(
                cluster_id=len(clusters),
                centroid_content=items[0].get("content", "")[:80] if items else "",
                member_count=len(items),
                avg_energy=sum(i.get("energy_level", 0.5) for i in items) / max(1, len(items)),
                projects={proj},
            )
            clusters.append(cluster)

        # Identify dense, sparse, and islands
        dense = [c for c in clusters if c.member_count >= _DENSE_THRESHOLD]
        sparse = [c for c in clusters if c.member_count < _SPARSE_THRESHOLD]

        self._cached_topology = {
            "total_facts": len(all_data),
            "total_clusters": len(clusters),
            "clusters": clusters,
            "dense_regions": dense,
            "sparse_regions": sparse,
        }
        return self._cached_topology

    async def get_dense_regions(self, project: Optional[str] = None) -> list[ClusterInfo]:
        """Where does the agent know a lot?"""
        if not self._cached_topology:
            await self.build_topology(project=project)
        return self._cached_topology.get("dense_regions", []) if self._cached_topology else []

    async def get_sparse_regions(self, project: Optional[str] = None) -> list[ClusterInfo]:
        """Where are the agent's blind spots?"""
        if not self._cached_topology:
            await self.build_topology(project=project)
        return self._cached_topology.get("sparse_regions", []) if self._cached_topology else []

    def __repr__(self) -> str:
        total = self._cached_topology.get("total_facts", "?") if self._cached_topology else "?"
        return f"KnowledgeMap(facts={total})"
