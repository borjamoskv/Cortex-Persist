import numpy as np
import random
from typing import List, Dict
from cortex.interfaces.memory_provider import MemoryProvider, MemoryNode, IntentVector
from cortex.simulation.primitives import MemoryParticle, MemoryTrajectory
from cortex.simulation.thermodynamics import MemoryFrictionEngine


class MonteCarloRecallEngine:
    """
    Simulates probabilistic memory paths through the Graph Manifold based on intent alignment.
    Includes Thermodynamic Friction and Momentum.
    """

    def __init__(self, provider: MemoryProvider):
        self.provider = provider
        self.friction_engine = MemoryFrictionEngine()

    def _softmax(self, x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        # Prevent division by zero
        t = max(0.01, temperature)
        e_x = np.exp((x - np.max(x)) / t)
        return e_x / e_x.sum()

    def simulate(
        self,
        start_nodes: list[MemoryNode],
        intent: IntentVector,
        n_samples: int = 50,
        max_steps: int = 3,
        temperature: float = 1.2,
        momentum_factor: float = 0.8,
    ) -> list[MemoryTrajectory]:

        trajectories = []
        node_cache: dict[str, MemoryNode] = {n.id: n for n in start_nodes}
        intent_vec = np.array(intent.semantic_vector)
        norm_intent = np.linalg.norm(intent_vec)

        for _i in range(n_samples):
            current_node = random.choice(start_nodes)
            particle = MemoryParticle.from_node(current_node)
            path = [particle]

            # Momentum initialization (p_t)
            current_momentum = intent_vec.copy()

            for step in range(max_steps):
                causal_edges = self.provider.causal_edges(current_node.id)
                if not causal_edges:
                    break

                transition_weights = []
                neighbors_eval = []

                for source_id, target_id, edge_w in causal_edges:
                    neighbor_id = target_id if source_id == current_node.id else source_id

                    if neighbor_id not in node_cache:
                        n_list = self.provider.neighbors(neighbor_id)
                        if n_list:
                            node_cache[neighbor_id] = n_list[0]

                    if neighbor_id in node_cache:
                        neighbor_node = node_cache[neighbor_id]
                        neighbors_eval.append(neighbor_node)

                        alignment = 0.1
                        sim = 0.1
                        temporal_gap = abs(neighbor_node.timestamp - current_node.timestamp)

                        if isinstance(neighbor_node.embedding, (list, np.ndarray)):
                            v_n = np.array(neighbor_node.embedding)
                            norm_n = np.linalg.norm(v_n)
                            if norm_n > 0 and norm_intent > 0:
                                sim = np.dot(intent_vec, v_n) / (norm_intent * norm_n)
                                # Momentum alignment
                                alignment = np.dot(current_momentum, v_n) / (
                                    np.linalg.norm(current_momentum) * norm_n
                                )

                        # Calculate Thermodynamic Friction
                        friction = self.friction_engine.compute_friction(
                            hop_distance=step + 1,
                            semantic_similarity=sim,
                            temporal_gap=temporal_gap,
                        )

                        # Apply friction as a penalty to transition weight
                        w = edge_w * max(0.01, alignment) * np.exp(-friction)
                        transition_weights.append(w)

                if not transition_weights:
                    break

                tw_array = np.array(transition_weights)
                probs = self._softmax(tw_array, temperature=temperature)

                next_idx = np.random.choice(len(neighbors_eval), p=probs)
                next_node = neighbors_eval[next_idx]

                # Update Momentum: p_{t+1} = p_t * momentum + new_sample * (1 - momentum)
                if isinstance(next_node.embedding, (list, np.ndarray)):
                    v_n = np.array(next_node.embedding)
                    current_momentum = (current_momentum * momentum_factor) + (
                        v_n * (1.0 - momentum_factor)
                    )
                    current_momentum = current_momentum / np.linalg.norm(current_momentum)

                particle = MemoryParticle.from_node(next_node, initial_mass=probs[next_idx])
                # Entropy increases with friction
                particle.entropy += 0.1 * step + (1.0 - probs[next_idx])

                path.append(particle)
                current_node = next_node

            traj = MemoryTrajectory(particles=path)
            traj.intent_alignment = float(np.mean([p.probability_mass for p in path]))
            traj.entropy_penalty = float(np.mean([p.entropy for p in path]))
            trajectories.append(traj)

        return trajectories
