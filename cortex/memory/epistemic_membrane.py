import hashlib
import time
import torch
import torchhd
from torchhd import functional as F
from torchhd.structures import ItemMemory
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

D = 16384
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class MerkleLedger:
    """
    Append-only cryptographic ledger to track Epistemic Membrane validations.
    Ensures that every hypervector commit is tamper-evident.
    """
    def __init__(self):
        self.leaves = []  # (hv_hash, hv_binary, metadata)
    
    def hash_hv(self, hv: torch.Tensor) -> bytes:
        """Deterministic and compact hashing of a hypervector."""
        # Convert to binary representation for compact hashing
        binary = (hv > 0).cpu().numpy().astype(np.int8).tobytes()
        return hashlib.sha256(binary).digest()
    
    def append(self, hv: torch.Tensor, membrane_result: Dict, source_llm_hash: str = None) -> str:
        """Appends a new verified leaf to the ledger."""
        hv_hash = self.hash_hv(hv)
        leaf = {
            "hash": hv_hash.hex(),
            "sim_max": membrane_result.get("max_similarity", 1.0),
            "accepted": membrane_result.get("accept", True),
            "timestamp": time.time(),
            "llm_source": source_llm_hash
        }
        self.leaves.append(leaf)
        return self._compute_root()
    
    def _compute_root(self) -> str:
        """
        Computes the current Merkle root based on all leaves.
        This provides a simplified linear hash chain for the root.
        """
        if not self.leaves:
            return hashlib.sha256(b"genesis").hexdigest()
        
        hasher = hashlib.sha256()
        for leaf in self.leaves:
            hasher.update(leaf["hash"].encode('utf-8'))
        return hasher.hexdigest()

class EpistemicMembrane:
    """
    Active epistemic containment and self-maintenance using VSA/HDC.
    Transforms memory into a membrane that validates, protects, and autopoietically evolves.
    """
    def __init__(self, dim: int = D, max_history: int = 10000):
        self.dim = dim
        self.item_memory = ItemMemory(dim, max_history)
        
        # Base roles for structural and semantic binding
        self.roles = {
            "consistency": torchhd.random(1, dim, device=device)[0],
            "novelty": torchhd.random(1, dim, device=device)[0],
            "temporal": torchhd.random(1, dim, device=device)[0],
            "graph_node": torchhd.random(1, dim, device=device)[0],
            "graph_edge": torchhd.random(1, dim, device=device)[0],
        }
        
        # Epistemic Boundaries
        self.threshold_consistency = 0.68
        self.threshold_novelty = 0.88   # Below this implies it is novel enough
        self.noise_tolerance = 0.25     # Maximum acceptable noise/flip percentage
        
        # Cryptographic continuity
        self.ledger = MerkleLedger()

    def permute_temporal(self, hv: torch.Tensor, timestep: int) -> torch.Tensor:
        """Progressive permutation to encode time, yielding a natural similarity decay."""
        return F.permute(hv, shifts=timestep % 512)

    def encode_graph(self, nodes: List[torch.Tensor], edges: List[Tuple[int, int]]) -> torch.Tensor:
        """Encodes a graph topology (nodes + edges) into a single Hypervector."""
        hv = torch.zeros(self.dim, device=device)
        
        # Bind nodes with their spatial/topological sequence
        for i, node in enumerate(nodes):
            node_hv = F.bind(self.roles["graph_node"], node)
            node_hv = F.permute(node_hv, shifts=i)
            hv = F.bundle(hv, node_hv)
        
        # Bind edges (source -> destination)
        for src, dst in edges:
            edge = F.bind(nodes[src], nodes[dst])
            edge_hv = F.bind(self.roles["graph_edge"], edge)
            hv = F.bundle(hv, edge_hv)
        
        return F.normalize(hv)

    def encode_episode(self, components: List[Tuple[str, torch.Tensor]], timestep: int = 0) -> torch.Tensor:
        """Encodes a full episodic event from components with temporal grounding."""
        hv = torch.zeros(self.dim, device=device)
        for role_name, filler in components:
            if role_name not in self.roles:
                self.roles[role_name] = torchhd.random(1, self.dim, device=device)[0]
            role = self.roles[role_name]
            
            bound = F.bind(role, filler)
            bound = self.permute_temporal(bound, timestep)
            hv = F.bundle(hv, bound)
            
        return F.normalize(hv)

    def _cleanup(self, hv: torch.Tensor) -> torch.Tensor:
        """Helper to cleanup a hypervector using the ItemMemory."""
        if len(self.item_memory) == 0:
            return hv
        # Standard torchhd ItemMemory forward pass returns similarity scores
        # We find the argmax to get the closest original vector.
        sims = F.cosine_similarity(hv.unsqueeze(0), self.item_memory.weight)
        best_idx = sims.argmax().item()
        return self.item_memory.weight[best_idx]

    def check_proposal(self, proposal_hv: torch.Tensor) -> Dict:
        """
        Validates if a new proposal respects the epistemic boundary.
        Checks for consistency, novelty, and tamper/noise levels.
        """
        if len(self.item_memory) == 0:
            return {"accept": True, "reason": "first_commit", "confidence": 1.0, "max_similarity": 1.0}

        # Query existing memory for similarity
        sims = F.cosine_similarity(proposal_hv.unsqueeze(0), self.item_memory.weight)
        
        max_sim = sims.max().item()
        avg_sim = sims.mean().item()
        best_idx = sims.argmax().item()
        
        consistency = max_sim >= self.threshold_consistency
        novelty = max_sim <= self.threshold_novelty
        
        # Tamper / noise detection via cleanup
        cleaned = self._cleanup(proposal_hv)
        noise_level = 1.0 - F.cosine_similarity(proposal_hv.unsqueeze(0), cleaned.unsqueeze(0)).item()
        
        accept = consistency and novelty and noise_level < self.noise_tolerance
        
        return {
            "accept": accept,
            "max_similarity": max_sim,
            "avg_similarity": avg_sim,
            "noise_level": noise_level,
            "reason": "consistent_novel" if accept else "inconsistent_or_noisy",
            "nearest_index": best_idx,
            "suggestions": "refine_conflict" if not consistency else "increase_novelty" if not novelty else "reduce_noise"
        }

    def commit(self, proposal_hv: torch.Tensor, metadata: Dict = None, source_llm_hash: str = None) -> str:
        """
        Commits the proposal to the VSA memory and appends to the cryptographic ledger.
        """
        # Add to HDC item memory (this extends self.item_memory.weight)
        # ItemMemory in torchhd expects add() if implemented, or we can concatenate.
        # We use standard .add() assuming it's supported by the VSA setup or extending ItemMemory.
        if hasattr(self.item_memory, 'add'):
            self.item_memory.add(proposal_hv)
        else:
            # Fallback for standard torchhd ItemMemory if .add() isn't native
            new_weight = torch.cat([self.item_memory.weight, proposal_hv.unsqueeze(0)], dim=0)
            self.item_memory.weight = torch.nn.Parameter(new_weight)
            self.item_memory.num_embeddings += 1
            
        # Add to Merkle Ledger
        membrane_result = metadata if metadata else {"max_similarity": 1.0, "accept": True}
        root_hash = self.ledger.append(proposal_hv, membrane_result, source_llm_hash)
        
        return root_hash

    def detect_and_mutate(self, recent_proposals: List[torch.Tensor], generations: int = 3) -> Tuple[Optional[torch.Tensor], Optional[Dict]]:
        """
        Autopoietic Mutation: Adjusts the epistemic membrane if global coherence drops.
        Generates a controlled mutant that anchors back to historical memory.
        """
        if not recent_proposals:
            return None, None
            
        global_hv = torch.zeros(self.dim, device=device)
        for p in recent_proposals:
            global_hv = F.bundle(global_hv, p)
        global_hv = F.normalize(global_hv)
        
        # Calculate coherence across recent proposals
        recent_stack = torch.stack(recent_proposals)
        coherence = F.cosine_similarity(global_hv.unsqueeze(0), recent_stack).mean().item()
        
        if coherence < 0.55:  # Epistemic crisis threshold
            # Mutate: controlled superposition + noise
            mutation = global_hv
            for _ in range(generations):
                noise = torchhd.random(1, self.dim, device=device)[0] * 0.15
                mutation = F.bundle(mutation, noise)
                mutation = F.normalize(mutation)
            
            # Cleanup against historical memory to anchor the mutation
            cleaned = self._cleanup(mutation)
            return cleaned, {"mutation_type": "autopoietic_realignment", "old_coherence": coherence}
            
        return None, None
