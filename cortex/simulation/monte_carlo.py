import numpy as np
import random
from typing import List, Dict, Tuple
from cortex.interfaces.memory_provider import MemoryProvider, MemoryNode, IntentVector
from cortex.simulation.primitives import MemoryParticle, MemoryTrajectory

class MonteCarloRecallEngine:
    """
    Simulates probabilistic memory paths through the Graph Manifold based on intent alignment.
    """
    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    def _softmax(self, x: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        e_x = np.exp((x - np.max(x)) / temperature)
        return e_x / e_x.sum()

    def simulate(self, 
                 start_nodes: List[MemoryNode], 
                 intent: IntentVector, 
                 n_samples: int = 50,
                 max_steps: int = 3,
                 temperature: float = 1.2) -> List[MemoryTrajectory]:
        
        trajectories = []
        
        # Pre-cache nodes for performance in simulation
        node_cache: Dict[str, MemoryNode] = {n.id: n for n in start_nodes}
        
        intent_vec = np.array(intent.semantic_vector)
        norm_intent = np.linalg.norm(intent_vec)
        
        for i in range(n_samples):
            # Pick a random start node, weighted by intent similarity if we want, or uniform
            current_node = random.choice(start_nodes)
            particle = MemoryParticle.from_node(current_node)
            path = [particle]
            
            for step in range(max_steps):
                causal_edges = self.provider.causal_edges(current_node.id)
                if not causal_edges:
                    break
                    
                # Evaluate transitions
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
                        
                        # Calculate intent alignment
                        alignment = 0.1
                        if isinstance(neighbor_node.embedding, (list, np.ndarray)):
                            v_n = np.array(neighbor_node.embedding)
                            norm_n = np.linalg.norm(v_n)
                            if norm_n > 0 and norm_intent > 0:
                                alignment = np.dot(intent_vec, v_n) / (norm_intent * norm_n)
                                
                        # Transition matrix weight = edge_weight * alignment (with temp applied later)
                        transition_weights.append(edge_w * max(0.01, alignment))
                
                if not transition_weights:
                    break
                    
                # Softmax over available transitions
                tw_array = np.array(transition_weights)
                probs = self._softmax(tw_array, temperature=temperature)
                
                # Sample next node
                next_idx = np.random.choice(len(neighbors_eval), p=probs)
                next_node = neighbors_eval[next_idx]
                
                # Update particle state (entropy increases with walk depth)
                particle = MemoryParticle.from_node(next_node, initial_mass=probs[next_idx])
                particle.entropy += 0.1 * step
                
                path.append(particle)
                current_node = next_node
                
            traj = MemoryTrajectory(particles=path)
            
            # Simple heuristic scoring for the trajectory
            traj.intent_alignment = float(np.mean([p.probability_mass for p in path]))
            traj.entropy_penalty = float(np.mean([p.entropy for p in path]))
            trajectories.append(traj)
            
        return trajectories
