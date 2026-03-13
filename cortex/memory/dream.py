"""CORTEX v8 — Associative Dream Engine (REM Phase).

The creative counterpart to HippocampalReplay (NREM).
While NREM consolidates and compresses, REM CREATES:

  1. Cluster Detection: Identifies emergent semantic clusters
  2. Synthetic Bridging: Generates "what-if" connections between distant concepts
  3. Emotional Re-weighting: Adjusts valence based on post-interaction feedback

Biological basis:
  - REM sleep produces bizarre, creative associations (dream logic)
  - Memory consolidation during REM focuses on emotional integration
  - Creative insights often emerge from REM-phase neural activity

Together with HippocampalReplay:
  NREM (SCE) → Compress, merge, reinforce → Stability
  REM  (ADE) → Bridge, restructure, reweight → Creativity

Derivation: Ω₅ (Antifragile by Default) + Ω₄ (Aesthetic Integrity)
  → Stress the knowledge graph to discover hidden connections.
    Beautiful bridges emerge from structured randomness.
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Final

logger = logging.getLogger("cortex.memory.dream")

__all__ = ["AssociativeDreamEngine", "DreamResult"]

# ─── Constants ────────────────────────────────────────────────────────

# Minimum cluster size to be considered meaningful
MIN_CLUSTER_SIZE: Final[int] = 2

# Maximum synthetic bridges generated per dream cycle
MAX_BRIDGES_PER_CYCLE: Final[int] = 10

# Minimum similarity for two engrams to be in the same cluster
CLUSTER_SIMILARITY_THRESHOLD: Final[float] = 0.75

# Maximum distance for bridge candidates (sweet spot: not too close, not too far)
BRIDGE_MIN_DISTANCE: Final[float] = 0.3
BRIDGE_MAX_DISTANCE: Final[float] = 0.7

# Emotional re-weighting strength
REWEIGHT_FACTOR: Final[float] = 0.1


# ─── Data Models ──────────────────────────────────────────────────────


@dataclass(slots=True)
class DreamResult:
    """Result of a single REM dream cycle."""

    clusters_found: int = 0
    bridges_created: int = 0
    engrams_reweighted: int = 0
    redundant_nodes_fused: int = 0
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def total_operations(self) -> int:
        return (
            self.clusters_found
            + self.bridges_created
            + self.engrams_reweighted
            + self.redundant_nodes_fused
        )


@dataclass(slots=True)
class SemanticCluster:
    """A group of semantically related engrams discovered during dreaming."""

    cluster_id: str
    member_ids: list[str] = field(default_factory=list)
    centroid: list[float] = field(default_factory=list)
    avg_similarity: float = 0.0
    dominant_project: str = ""


@dataclass(slots=True, frozen=True)
class SyntheticBridge:
    """A creative connection between two distant engram clusters."""

    source_cluster_id: str
    target_cluster_id: str
    source_engram_id: str
    target_engram_id: str
    semantic_distance: float
    bridge_hypothesis: str = ""


# ─── Utility Functions ────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """O(d) cosine similarity."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _compute_centroid(embeddings: list[list[float]]) -> list[float]:
    """Compute centroid of a list of embeddings."""
    if not embeddings:
        return []
    dim = len(embeddings[0])
    centroid = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            centroid[i] += emb[i]
    n = len(embeddings)
    return [c / n for c in centroid]


# ─── Dream Engine ─────────────────────────────────────────────────────


class AssociativeDreamEngine:
    """REM-phase dream engine for creative knowledge restructuring.

    Runs during daemon idle periods AFTER HippocampalReplay (NREM).
    Does not replace NREM — complements it with creative operations:

    1. Detect clusters of semantically related engrams
    2. Bridge distant clusters with synthetic hypotheses
    3. Re-weight emotional valence based on global coherence
    4. Fuse redundant nodes to reduce graph entropy

    Usage:
        engine = AssociativeDreamEngine(vector_store=my_vector_store)
        result = await engine.dream_cycle(tenant_id="default")
    """

    __slots__ = ("_vs", "_bridge_min", "_bridge_max", "_cluster_threshold")

    def __init__(
        self,
        vector_store: Any = None,
        cluster_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
        bridge_min_distance: float = BRIDGE_MIN_DISTANCE,
        bridge_max_distance: float = BRIDGE_MAX_DISTANCE,
    ) -> None:
        self._vs = vector_store
        self._cluster_threshold = cluster_threshold
        self._bridge_min = bridge_min_distance
        self._bridge_max = bridge_max_distance

    async def dream_cycle(
        self,
        tenant_id: str,
        engrams: list[Any] | None = None,
    ) -> DreamResult:
        """Execute one REM dream cycle.

        Args:
            tenant_id: Isolation scope.
            engrams: Pre-fetched engrams. If None, fetches from vector store.

        Returns:
            DreamResult with aggregate stats.
        """
        start = time.monotonic()
        result = DreamResult()

        # Fetch engrams if not provided
        if engrams is None and self._vs and hasattr(self._vs, "scan_engrams"):
            engrams = await self._vs.scan_engrams(tenant_id)

        if not engrams or len(engrams) < MIN_CLUSTER_SIZE:
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        # Phase 1: Cluster Detection
        clusters = self._detect_clusters(engrams)
        result.clusters_found = len(clusters)

        # Phase 2: Redundancy Fusion (within clusters)
        result.redundant_nodes_fused = await self._fuse_redundant(clusters, engrams)

        # Phase 3: Synthetic Bridging (between clusters)
        bridges = self._generate_bridges(clusters)
        result.bridges_created = len(bridges)

        # Phase 4: Emotional Re-weighting
        result.engrams_reweighted = self._emotional_reweight(engrams)

        result.duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "REM dream cycle: %d clusters, %d bridges, %d reweighted, %d fused in %.1fms",
            result.clusters_found,
            result.bridges_created,
            result.engrams_reweighted,
            result.redundant_nodes_fused,
            result.duration_ms,
        )

        return result

    # ─── Phase 1: Cluster Detection ───────────────────────────────

    def _detect_clusters(self, engrams: list[Any]) -> list[SemanticCluster]:
        """Greedy agglomerative clustering based on semantic similarity."""
        if not engrams:
            return []

        assigned: set[int] = set()
        clusters: list[SemanticCluster] = []
        cluster_idx = 0

        # Pre-extract embeddings for faster iteration
        embs = [getattr(e, "embedding", None) for e in engrams]

        for i, emb_a in enumerate(embs):
            if i in assigned or not emb_a:
                continue

            cluster_members = self._expand_cluster(i, emb_a, embs, assigned)

            if len(cluster_members) >= MIN_CLUSTER_SIZE:
                clusters.append(self._build_cluster(cluster_members, engrams, cluster_idx))
                cluster_idx += 1

        return clusters

    def _expand_cluster(
        self, i: int, emb_a: list[float], embs: list[Any], assigned: set[int]
    ) -> list[int]:
        """Find all engrams similar to the centroid candidate."""
        members = [i]
        assigned.add(i)

        for j in range(i + 1, len(embs)):
            if j in assigned or not embs[j]:
                continue
            if _cosine_similarity(emb_a, embs[j]) >= self._cluster_threshold:
                members.append(j)
                assigned.add(j)
        return members

    def _build_cluster(self, members: list[int], engrams: list[Any], idx: int) -> SemanticCluster:
        """Construct a SemanticCluster from its constituents."""
        e_embs = [getattr(engrams[m], "embedding", []) for m in members]
        centroid = _compute_centroid([e for e in e_embs if e])
        dominant = self._compute_dominant_project(members, engrams)
        avg_sim = self._compute_cluster_avg_similarity(members, engrams)

        return SemanticCluster(
            cluster_id=f"cluster_{idx}",
            member_ids=[getattr(engrams[m], "id", str(m)) for m in members],
            centroid=centroid,
            avg_similarity=avg_sim,
            dominant_project=dominant,
        )

    def _compute_dominant_project(self, cluster_members: list[int], engrams: list[Any]) -> str:
        """Find the most frequent project_id in a cluster."""
        projects: dict[str, int] = defaultdict(int)
        for m in cluster_members:
            pid = getattr(engrams[m], "project_id", "unknown")
            projects[pid] += 1
        return max(projects, key=projects.get) if projects else ""  # type: ignore[arg-type]

    def _compute_cluster_avg_similarity(
        self, cluster_members: list[int], engrams: list[Any]
    ) -> float:
        """Compute the average pairwise cosine similarity of all engrams in the cluster."""
        if len(cluster_members) <= 1:
            return 0.0

        sims: list[float] = []
        for ci in range(len(cluster_members)):
            for cj in range(ci + 1, len(cluster_members)):
                ea = getattr(engrams[cluster_members[ci]], "embedding", [])
                eb = getattr(engrams[cluster_members[cj]], "embedding", [])
                if ea and eb:
                    sims.append(_cosine_similarity(ea, eb))
        return sum(sims) / len(sims) if sims else 0.0

    # ─── Phase 2: Redundancy Fusion ───────────────────────────────

    async def _fuse_redundant(self, clusters: list[SemanticCluster], engrams: list[Any]) -> int:
        """Within each cluster, fuse engrams that are near-identical.

        Near-identical = similarity > 0.95. Keeps the newer engram
        and marks the older one for deletion.
        """
        if not self._vs or not hasattr(self._vs, "delete"):
            return 0

        # Build ID → engram lookup
        id_to_engram: dict[str, Any] = {e.id: e for e in engrams if getattr(e, "id", None)}

        fused = 0
        for cluster in clusters:
            members = [id_to_engram[mid] for mid in cluster.member_ids if mid in id_to_engram]
            to_delete = self._identify_redundant_engrams(members)

            for vid in to_delete:
                await self._vs.delete(vid)
                fused += 1
                logger.debug("REM fused redundant engram: %s", vid)

        return fused

    def _identify_redundant_engrams(self, members: list[Any]) -> set[str]:
        """Identify older engrams in a cluster that are near-identical to newer ones >0.95 sim."""
        to_delete: set[str] = set()

        valid = [
            (getattr(m, "id", ""), getattr(m, "embedding", []), getattr(m, "timestamp", 0))
            for m in members
            if getattr(m, "id", "") and getattr(m, "embedding", [])
        ]

        for i, (id_a, emb_a, ts_a) in enumerate(valid):
            if id_a in to_delete:
                continue
            self._mark_redundancies(i, id_a, emb_a, ts_a, valid, to_delete)

        return to_delete

    def _mark_redundancies(
        self,
        i: int,
        id_a: str,
        emb_a: list[float],
        ts_a: float,
        valid: list[Any],
        to_delete: set[str],
    ) -> None:
        """Mark identical pairs for deletion."""
        for j in range(i + 1, len(valid)):
            id_b, emb_b, ts_b = valid[j]
            if id_b in to_delete:
                continue

            if _cosine_similarity(emb_a, emb_b) > 0.95:
                to_delete.add(id_a if ts_a < ts_b else id_b)

    def _generate_bridges(self, clusters: list[SemanticCluster]) -> list[SyntheticBridge]:
        """Generate creative bridges between distant clusters.

        The "sweet spot" for creativity: clusters that are neither too
        similar (boring) nor too different (nonsensical).
        """
        bridges: list[SyntheticBridge] = []

        for i, cluster_a in enumerate(clusters):
            if not cluster_a.centroid:
                continue

            for j in range(i + 1, len(clusters)):
                cluster_b = clusters[j]
                if not cluster_b.centroid:
                    continue

                bridge = self._create_bridge_if_eligible(cluster_a, cluster_b)
                if bridge:
                    bridges.append(bridge)
                    if len(bridges) >= MAX_BRIDGES_PER_CYCLE:
                        return bridges

        return bridges

    def _create_bridge_if_eligible(
        self, ca: SemanticCluster, cb: SemanticCluster
    ) -> SyntheticBridge | None:
        """Create a bridge hypothesis if semantic distance is in sweet spot."""
        sim = _cosine_similarity(ca.centroid, cb.centroid)
        distance = 1.0 - sim

        if self._bridge_min <= distance <= self._bridge_max:
            return SyntheticBridge(
                source_cluster_id=ca.cluster_id,
                target_cluster_id=cb.cluster_id,
                source_engram_id=(ca.member_ids[0] if ca.member_ids else ""),
                target_engram_id=(cb.member_ids[0] if cb.member_ids else ""),
                semantic_distance=round(distance, 4),
                bridge_hypothesis=(
                    f"What connects {ca.dominant_project} and {cb.dominant_project}?"
                ),
            )
        return None

    # ─── Phase 4: Emotional Re-weighting ──────────────────────────

    def _emotional_reweight(self, engrams: list[Any]) -> int:
        """Adjust emotional valence based on global coherence.

        Engrams that are well-connected (high entangled_refs) get
        a positive valence boost. Isolated engrams get dampened.

        This simulates the REM-phase emotional integration process.
        """
        reweighted = 0

        for engram in engrams:
            refs = getattr(engram, "entangled_refs", [])
            energy = getattr(engram, "energy_level", 0.5)
            metadata = getattr(engram, "metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            # Well-connected → boost
            if len(refs) >= 3 and energy > 0.5:
                current_valence = metadata.get("dream_valence", 0.0)
                new_valence = min(1.0, current_valence + REWEIGHT_FACTOR)
                metadata["dream_valence"] = round(new_valence, 3)
                metadata["dream_cycle"] = time.time()
                reweighted += 1

            # Very isolated + low energy → dampen
            elif len(refs) == 0 and energy < 0.3:
                current_valence = metadata.get("dream_valence", 0.0)
                new_valence = max(-1.0, current_valence - REWEIGHT_FACTOR)
                metadata["dream_valence"] = round(new_valence, 3)
                metadata["dream_cycle"] = time.time()
                reweighted += 1

        return reweighted

    def __repr__(self) -> str:
        return (
            f"AssociativeDreamEngine("
            f"cluster_threshold={self._cluster_threshold}, "
            f"bridge_range=[{self._bridge_min}, {self._bridge_max}])"
        )
