from cortex.interfaces.memory_provider import (
    MemoryProvider,
    IntentVector,
    MemoryNode,
    MemorySubgraph,
)
from cortex.semantic.graph_engine import GraphExpansionEngine
from cortex.semantic.coherence import CoherenceScorer
import numpy as np
import random


class HybridRetriever:
    """
    Coordinates semantic vector search, graph expansion, and coherence scoring.
    """

    def __init__(self, provider: MemoryProvider):
        self.provider = provider
        self.graph_engine = GraphExpansionEngine(provider)

    def retrieve(self, query: str, intent: IntentVector, k: int = 10) -> MemorySubgraph:
        # Phase 1: Vector Search
        # Uses purely the semantic vector from the intent encoder
        candidates = self.provider.vector_search(intent.semantic_vector, limit=50)

        if not candidates:
            # Degenerate case
            return MemorySubgraph(root_query=query, nodes=[], edges=[], coherence_score=0.0)

        # Phase 2: Graph Expansion (k-hop constrained)
        # Expansion bridges nodes using causal links and connectivity
        expanded_nodes, edges = self.graph_engine.expand(
            seeds=candidates, hops=2, causal_weight=0.7
        )

        # Phase 3: Rerank (intent-aware)
        def rank_score(node: MemoryNode) -> float:
            base_score = 0.0
            if isinstance(node.embedding, list | np.ndarray) and isinstance(
                intent.semantic_vector, list | np.ndarray
            ):
                v1 = np.array(node.embedding)
                v2 = np.array(intent.semantic_vector)
                n1 = np.linalg.norm(v1)
                n2 = np.linalg.norm(v2)
                if n1 > 0 and n2 > 0:
                    base_score = np.dot(v1, v2) / (n1 * n2)

            # temporal bias
            temporal_bonus = 0.0
            if intent.temporal_bias > 0.5 and node.timestamp > 0:
                # favor newer nodes or explicit time constraints
                temporal_bonus = 0.1

            return float(base_score + temporal_bonus)

        expanded_nodes.sort(key=rank_score, reverse=True)

        # Phase 4: Coherence Filter and ε-retrieval (Random exploration channel)
        # Drop noise by taking top K, but inject 15% random nodes from the expanded frontier to avoid collapse
        epsilon = 0.15
        num_random = max(1, int(k * epsilon))
        num_top = k - num_random

        top_k_nodes = expanded_nodes[:num_top]

        # Inject random exploration nodes from the remaining pool
        remaining_nodes = expanded_nodes[num_top:]
        if remaining_nodes:
            # sample without replacement if enough nodes
            sample_size = min(num_random, len(remaining_nodes))
            random_nodes = random.sample(remaining_nodes, sample_size)
            top_k_nodes.extend(random_nodes)

        # Filter edges to only those connecting top K nodes
        top_k_ids = {n.id for n in top_k_nodes}
        top_k_edges = [(s, t, w) for s, t, w in edges if s in top_k_ids and t in top_k_ids]

        coherence = CoherenceScorer.score(top_k_nodes, top_k_edges)

        # Phase 5: Hydrate ONLY the final K nodes
        hydrated_nodes = self.provider.hydrate(top_k_nodes)

        return MemorySubgraph(
            root_query=query, nodes=hydrated_nodes, edges=top_k_edges, coherence_score=coherence
        )
