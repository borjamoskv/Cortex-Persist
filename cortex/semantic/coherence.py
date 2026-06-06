import numpy as np

from cortex.interfaces.memory_provider import MemoryNode


class CoherenceScorer:
    """
    Measures if the subgraph makes 'human sense'.
    coherence = density(causal_edges) + embedding_consistency - temporal_noise - anti_coherence
    """

    @staticmethod
    def score(nodes: list[MemoryNode], edges: list[tuple[str, str, float]]) -> float:
        if not nodes:
            return 0.0

        N = len(nodes)

        # 1. Edge density
        possible_edges = N * (N - 1)
        density = len(edges) / possible_edges if possible_edges > 0 else 1.0

        # 2. Embedding consistency (average pairwise cosine similarity)
        consistency = 0.0
        if N > 1:
            sims = []
            for i in range(N):
                for j in range(i + 1, N):
                    e1 = nodes[i].embedding
                    e2 = nodes[j].embedding
                    if isinstance(e1, list | np.ndarray) and isinstance(e2, list | np.ndarray):
                        v1 = np.array(e1)
                        v2 = np.array(e2)
                        n1 = np.linalg.norm(v1)
                        n2 = np.linalg.norm(v2)
                        if n1 > 0 and n2 > 0:
                            sim = np.dot(v1, v2) / (n1 * n2)
                            sims.append(float(sim))
            if sims:
                consistency = sum(sims) / len(sims)
        else:
            consistency = 1.0

        # 3. Temporal noise (variance in timestamps)
        temporal_noise = 0.0
        if N > 1:
            timestamps = [n.timestamp for n in nodes if n.timestamp > 0]
            if len(timestamps) > 1:
                std_dev = np.std(timestamps)
                mean_t = np.mean(timestamps)
                temporal_noise = float(std_dev / mean_t) if mean_t > 0 else 0.0
                temporal_noise = min(temporal_noise, 0.5)

        # 4. Anti-coherence term (detects overly perfect echo topology)
        # If consistency is too high (> 0.90) and density is very high, it's likely a hallucinated loop.
        anti_coherence = 0.0
        if consistency > 0.90 and density > 0.8:
            # The more "perfect" it looks beyond 0.90, the harder we punish it.
            anti_coherence = (consistency - 0.90) * 5.0  # Max penalty of 0.5

        coherence = density + consistency - temporal_noise - anti_coherence

        # Normalize to [0, 1] roughly
        return max(0.0, min(1.0, coherence / 2.0))
