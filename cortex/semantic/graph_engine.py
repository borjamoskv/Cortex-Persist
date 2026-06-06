import numpy as np
from cortex.interfaces.memory_provider import MemoryNode, MemoryProvider


class GraphExpansionEngine:
    """
    Expands memory nodes by traversing causal links, temporal adjacency, and semantic similarity.
    Includes Edge Entropy Decay to prevent exponential graph hallucination.
    """

    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    def expand(
        self, seeds: list[MemoryNode], hops: int = 2, causal_weight: float = 0.7
    ) -> tuple[list[MemoryNode], list[tuple[str, str, float]]]:
        expanded_nodes: dict[str, MemoryNode] = {node.id: node for node in seeds}
        edges: list[tuple[str, str, float]] = []

        current_frontier = seeds
        lambda_decay = 0.5  # Decay rate λ

        for hop in range(hops):
            next_frontier = []
            hop_penalty = np.exp(-lambda_decay * hop)

            for node in current_frontier:
                # Get causal neighbors
                causal_links = self.provider.causal_edges(node.id)
                for source_id, target_id, base_weight in causal_links:
                    # 1. Hop Decay
                    w = base_weight * causal_weight * hop_penalty

                    neighbor_id = target_id if source_id == node.id else source_id

                    # We might need semantic_distance_penalty here.
                    # We fetch the neighbor to compute it if possible.
                    if neighbor_id not in expanded_nodes:
                        neighbors = self.provider.neighbors(neighbor_id)
                        if neighbors:
                            neighbor_node = neighbors[0]

                            # 2. Semantic Distance Penalty
                            sem_penalty = 1.0
                            if isinstance(node.embedding, list | np.ndarray) and isinstance(
                                neighbor_node.embedding, list | np.ndarray
                            ):
                                v1 = np.array(node.embedding)
                                v2 = np.array(neighbor_node.embedding)
                                n1 = np.linalg.norm(v1)
                                n2 = np.linalg.norm(v2)
                                if n1 > 0 and n2 > 0:
                                    sim = np.dot(v1, v2) / (n1 * n2)
                                    sem_penalty = max(0.1, sim)  # Punish if semantically orthogonal

                            w = w * sem_penalty
                            edges.append((source_id, target_id, float(w)))

                            expanded_nodes[neighbor_node.id] = neighbor_node
                            next_frontier.append(neighbor_node)
                    else:
                        edges.append((source_id, target_id, float(w)))

            current_frontier = next_frontier
            if not current_frontier:
                break

        # Simple deduplication of edges
        unique_edges = list({(s, t): w for s, t, w in edges}.items())
        edges_out = [(s, t, w) for ((s, t), w) in unique_edges]

        return list(expanded_nodes.values()), edges_out
