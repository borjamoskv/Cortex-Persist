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
        result.engrams_reweighted = await self._emotional_reweight(engrams)

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
        """Greedy agglomerative clustering based on semantic similarity.

        O(n²) in engram count — acceptable for nightly batches of < 1000.
        For larger scales, use approximate methods.
        """
        if not engrams:
            return []

        # Build adjacency by similarity
        assigned: set[int] = set()
        clusters: list[SemanticCluster] = []
        cluster_idx = 0

        for i, engram_a in enumerate(engrams):
            if i in assigned:
                continue

            emb_a = getattr(engram_a, "embedding", None)
            if not emb_a:
                continue

            # Start new cluster
            cluster_members = [i]
            assigned.add(i)

            for j, engram_b in enumerate(engrams):
                if j in assigned or j == i:
                    continue

                emb_b = getattr(engram_b, "embedding", None)
                if not emb_b:
                    continue

                sim = _cosine_similarity(emb_a, emb_b)
                if sim >= self._cluster_threshold:
                    cluster_members.append(j)
                    assigned.add(j)

            if len(cluster_members) >= MIN_CLUSTER_SIZE:
                member_embeddings = [getattr(engrams[m], "embedding", []) for m in cluster_members]
                centroid = _compute_centroid([e for e in member_embeddings if e])

                # Detect dominant project
                projects: dict[str, int] = defaultdict(int)
                for m in cluster_members:
                    pid = getattr(engrams[m], "project_id", "unknown")
                    projects[pid] += 1
                dominant = max(projects, key=projects.get) if projects else ""  # type: ignore[arg-type]

                avg_sim = 0.0
                if len(cluster_members) > 1:
                    sims: list[float] = []
                    for ci in range(len(cluster_members)):
                        for cj in range(ci + 1, len(cluster_members)):
                            ea = getattr(engrams[cluster_members[ci]], "embedding", [])
                            eb = getattr(engrams[cluster_members[cj]], "embedding", [])
                            if ea and eb:
                                sims.append(_cosine_similarity(ea, eb))
                    avg_sim = sum(sims) / len(sims) if sims else 0.0

                clusters.append(
                    SemanticCluster(
                        cluster_id=f"cluster_{cluster_idx}",
                        member_ids=[getattr(engrams[m], "id", str(m)) for m in cluster_members],
                        centroid=centroid,
                        avg_similarity=avg_sim,
                        dominant_project=dominant,
                    )
                )
                cluster_idx += 1

        return clusters

    # ─── Phase 2: Redundancy Fusion ───────────────────────────────

    async def _fuse_redundant(self, clusters: list[SemanticCluster], engrams: list[Any]) -> int:
        """Within each cluster, fuse engrams that are near-identical.

        Near-identical = similarity > 0.95. Keeps the newer engram
        and marks the older one for deletion.
        """
        fused = 0

        # Build ID → engram lookup
        id_to_engram: dict[str, Any] = {}
        for e in engrams:
            eid = getattr(e, "id", None)
            if eid:
                id_to_engram[eid] = e

        for cluster in clusters:
            members = [id_to_engram.get(mid) for mid in cluster.member_ids]
            members = [m for m in members if m is not None]

            to_delete: set[str] = set()
            for i, ea in enumerate(members):
                if getattr(ea, "id", "") in to_delete:
                    continue
                emb_a = getattr(ea, "embedding", [])
                if not emb_a:
                    continue

                for j in range(i + 1, len(members)):
                    eb = members[j]
                    if getattr(eb, "id", "") in to_delete:
                        continue
                    emb_b = getattr(eb, "embedding", [])
                    if not emb_b:
                        continue

                    sim = _cosine_similarity(emb_a, emb_b)
                    if sim > 0.95:
                        # Keep the newer one (higher timestamp)
                        ts_a = getattr(ea, "timestamp", 0)
                        ts_b = getattr(eb, "timestamp", 0)
                        victim_id = getattr(ea if ts_a < ts_b else eb, "id", "")
                        if victim_id:
                            to_delete.add(victim_id)

            # Delete redundant engrams
            if to_delete and self._vs and hasattr(self._vs, "delete"):
                for vid in to_delete:
                    await self._vs.delete(vid)
                    fused += 1
                    logger.debug("REM fused redundant engram: %s", vid)

        return fused

    # ─── Phase 3: Synthetic Bridging ──────────────────────────────

    def _generate_bridges(self, clusters: list[SemanticCluster]) -> list[SyntheticBridge]:
        """Generate creative bridges between distant clusters.

        The "sweet spot" for creativity: clusters that are neither too
        similar (boring) nor too different (nonsensical).

        Distance in [BRIDGE_MIN, BRIDGE_MAX] → candidate bridge.
        """
        bridges: list[SyntheticBridge] = []

        for i, cluster_a in enumerate(clusters):
            if not cluster_a.centroid:
                continue

            for j in range(i + 1, len(clusters)):
                cluster_b = clusters[j]
                if not cluster_b.centroid:
                    continue

                sim = _cosine_similarity(cluster_a.centroid, cluster_b.centroid)
                distance = 1.0 - sim

                if self._bridge_min <= distance <= self._bridge_max:
                    # Sweet spot — create bridge hypothesis
                    bridge = SyntheticBridge(
                        source_cluster_id=cluster_a.cluster_id,
                        target_cluster_id=cluster_b.cluster_id,
                        source_engram_id=(cluster_a.member_ids[0] if cluster_a.member_ids else ""),
                        target_engram_id=(cluster_b.member_ids[0] if cluster_b.member_ids else ""),
                        semantic_distance=round(distance, 4),
                        bridge_hypothesis=(
                            f"What connects {cluster_a.dominant_project} "
                            f"and {cluster_b.dominant_project}?"
                        ),
                    )
                    bridges.append(bridge)

                    if len(bridges) >= MAX_BRIDGES_PER_CYCLE:
                        return bridges

        return bridges

    # ─── Phase 4: Emotional Re-weighting ──────────────────────────

    async def _emotional_reweight(self, engrams: list[Any]) -> int:
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
