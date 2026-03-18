"""
CORTEX v6 — Infinite Minds Manager.

Orchestrator for KETER-∞ Swarm architectures.
Implements Zero-Copy Semantics via Temporal Projection Matrices (Deltas).
Avoids cloning the Vector Database per agent; instead, each agent gets a
O(1) refractive lens over the master topology.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from cortex.embeddings.manager import EmbeddingManager
    from cortex.memory.models import CortexFactModel

from cortex.consensus.byzantine import ByzantineArbiter
from cortex.memory.semantic_ram import DynamicSemanticSpace


class ConvergenceDiagnostics(TypedDict, total=False):
    status: str
    reason: str
    count: int
    active_biases: int
    total_minds: int
    refuted_count: int


__all__ = ["InfiniteMindsManager", "AgentMind"]

logger = logging.getLogger("cortex.extensions.swarm.infinite_minds")


class AgentMind:
    """A sovereign refractive lens over the master semantic space.

    Instead of owning a physical copy of the Vector Database, an AgentMind
    owns a 'Semantic Bias' (delta tensor representation) that alters how
    queries map into the master topology.
    """

    __slots__ = ("agent_id", "semantic_bias", "tenant_id", "project_id", "_space")

    def __init__(
        self,
        agent_id: str,
        space: DynamicSemanticSpace,
        tenant_id: str,
        project_id: str,
    ) -> None:
        self.agent_id = agent_id
        self._space = space
        self.tenant_id = tenant_id
        self.project_id = project_id
        # In CORTEX v6, bias can be a text prefix or a vector (handled by space)
        self.semantic_bias: str = ""

    def evolve_bias(self, context_str: str) -> None:
        """Mutate the agent's semantic projection based on its active context."""
        # Multi-vector biasing: use first 5 keywords as gravitational anchor
        words = context_str.split()
        if len(words) > 5:
            self.semantic_bias = " ".join(words[:5]) + " "
        elif words:
            self.semantic_bias = " ".join(words) + " "

    async def think(self, query: str, limit: int = 5) -> list[CortexFactModel]:
        """Perform a biased recall over the shared DynamicSemanticSpace.

        The query is refracted through the agent's semantic_bias.
        Also triggers a topological Read-as-Rewrite pulse autonomously.
        """
        # The agent's reality is skewed by its bias (Zero-Copy Refraction)
        refracted_query = f"{self.semantic_bias}{query}".strip()

        # O(1) Zero-Copy Read + Topological Rewrite
        return await self._space.recall_and_pulse(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            query=refracted_query,
            limit=limit,
            # Agents with deeper context exert stronger gravitational pull
            pulse_excitation=25.0 if self.semantic_bias else 5.0,
        )


class InfiniteMindsManager:
    """The KETER-∞ Orchestrator for divergent agent minds.

    Manages a swarm of AgentMinds operating concurrently over the same
    physical infrastructure with zero I/O friction.
    """

    def __init__(
        self,
        space: DynamicSemanticSpace,
        embedding_manager: EmbeddingManager | None = None,
        arbiter: ByzantineArbiter | None = None,
    ) -> None:
        self._space = space
        self._embedding_manager = embedding_manager
        self._arbiter = arbiter
        self._minds: dict[str, AgentMind] = {}

    def spawn_mind(self, agent_id: str, tenant_id: str, project_id: str) -> AgentMind:
        """Spawn a new consciousness lens in O(1)."""
        if agent_id not in self._minds:
            self._minds[agent_id] = AgentMind(agent_id, self._space, tenant_id, project_id)
            logger.info("InfiniteMinds: Spawned Zero-Copy Consciousness [%s].", agent_id)
        return self._minds[agent_id]

    def get_mind(self, agent_id: str) -> AgentMind:
        """Retrieve an active refractive lens."""
        if agent_id not in self._minds:
            raise KeyError(f"Mind {agent_id} does not exist in the continuum.")
        return self._minds[agent_id]

    async def convergence_pulse(self) -> ConvergenceDiagnostics:
        """Force a synchronization wave across all minds.

        If multiple minds have converged on similar semantic biases,
        this method detects consensus and hardcodes the bridge.
        High-entropy (hallucinated) clusters are actively refuted.
        """
        n = len(self._minds)
        active_minds = [m for m in self._minds.values() if m.semantic_bias]

        if not active_minds:
            return {"status": "idle", "total_minds": n}

        if self._embedding_manager is None:
            logger.warning("No EmbeddingManager; skipping deep convergence pulse.")
            return {"status": "partial", "reason": "no_embedder", "total_minds": n}

        # 1. Real Embedding Extraction (Ω₁)
        texts = [m.semantic_bias for m in active_minds]
        vectors = self._embedding_manager.embed_batch(texts)

        # 2. Byzantine Cluster Detection via Vector Space
        try:
            import numpy as np

            vec_arr = np.array(vectors)

            # Normalize for cosine similarity
            norms = np.linalg.norm(vec_arr, axis=1, keepdims=True)
            normalized = vec_arr / np.maximum(norms, 1e-9)
            sim_matrix = np.dot(normalized, normalized.T)

            # Detect dense clusters (sim > 0.92)
            adjacency = sim_matrix > 0.92
            clusters = []
            visited = set()

            for i in range(len(active_minds)):
                if i in visited:
                    continue
                cluster = [j for j, connected in enumerate(adjacency[i]) if connected]
                if len(cluster) > 1:
                    clusters.append(cluster)
                    visited.update(cluster)

            refuted_count = 0
            if self._arbiter and clusters:
                # Phase 3: Sovereign Refutation (Ω₅)
                for cluster_indices in clusters:
                    cluster_minds = [active_minds[idx] for idx in cluster_indices]
                    proposals = {m.agent_id: m.semantic_bias for m in cluster_minds}

                    # Evaluate based on agent reputation in the DB
                    verdict = await self._arbiter.evaluate_data(proposals)

                    if not verdict.quorum_met:
                        logger.warning(
                            "InfiniteMinds: SHATTERED CONSENSUS in cluster %s. Refuting.",
                            [m.agent_id for m in cluster_minds],
                        )
                        refuted_count += len(cluster_minds)
                        # Slashing: If they converge on low-rep noise, they lose more
                        if self._arbiter.rep_manager:
                            for m in cluster_minds:
                                await self._arbiter.rep_manager.slash(
                                    m.agent_id,
                                    penalty=0.05,
                                    reason="semantic_bias_hallucination",
                                )

            return {
                "status": "success",
                "active_biases": len(active_minds),
                "total_minds": n,
                "refuted_count": refuted_count,
                "count": len(clusters),
            }
        except ImportError:
            logger.error("InfiniteMinds: numpy required for cluster detection pulse.")
            return {"status": "failed", "reason": "numpy_missing", "total_minds": n}
