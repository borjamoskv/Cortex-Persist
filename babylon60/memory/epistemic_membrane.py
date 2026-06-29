# [C5-REAL] Exergy-Maximized
from babylon60.crypto.hash_registry import cortex_hash, cortex_hash_raw
import hashlib
import time

import numpy as np
import torch  # pyright: ignore[reportMissingImports]
import torchhd  # pyright: ignore[reportMissingImports]
from torchhd import functional as F  # pyright: ignore[reportMissingImports]

D = 16384
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MerkleLedger:
    """
    Append-only cryptographic ledger to track Epistemic Membrane validations.
    Ensures that every hypervector commit is tamper-evident.
    """

    def __init__(self):
        self.leaves = []  # (hv_hash, hv_binary, metadata)
        self.current_root = cortex_hash(b"genesis")

    def hash_hv(self, hv: torch.Tensor) -> bytes:
        """Deterministic and compact hashing of a hypervector."""
        # Convert to binary representation for compact hashing
        binary = (hv > 0).cpu().numpy().astype(np.int8).tobytes()
        return cortex_hash_raw(binary)

    def append(self, hv: torch.Tensor, membrane_result: dict, source_llm_hash: str = None) -> str:  # pyright: ignore[reportArgumentType]
        """Appends a new verified leaf to the ledger."""
        hv_hash = self.hash_hv(hv)
        leaf = {
            "hash": hv_hash.hex(),
            "sim_max": membrane_result.get("max_similarity", 1.0),
            "accepted": membrane_result.get("accept", True),
            "timestamp": time.time(),
            "llm_source": source_llm_hash,
        }
        self.leaves.append(leaf)
        
        # O(1) Incremental Hash Chain Update:
        # H_n = SHA256(H_{n-1} + Leaf_hash)
        hasher = hashlib.sha256()
        hasher.update(self.current_root.encode("utf-8"))
        hasher.update(leaf["hash"].encode("utf-8"))
        self.current_root = hasher.hexdigest()
        return self.current_root

    def _compute_root(self) -> str:
        """
        Returns the current pre-calculated Merkle root.
        Maintains O(1) retrieval time.
        """
        return self.current_root


class EpistemicMembrane:
    """
    Active epistemic containment and self-maintenance using VSA/HDC.
    Transforms memory into a membrane that validates, protects, and autopoietically evolves.
    """

    def __init__(
        self,
        dim: int = D,
        max_history: int = 10000,
        threshold_consistency: float = 0.68,
        threshold_novelty: float = 0.88,
        noise_tolerance: float = 0.25,
        device: torch.device = None
    ):
        self.dim = dim
        self.max_history = max_history
        self.history = []  # List of past approved tensors

        # Set stable device for execution
        self.device = device if device is not None else torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Base roles for structural and semantic binding
        self.roles = {
            "consistency": torchhd.random(1, dim, device=self.device)[0],
            "novelty": torchhd.random(1, dim, device=self.device)[0],
            "temporal": torchhd.random(1, dim, device=self.device)[0],
            "graph_node": torchhd.random(1, dim, device=self.device)[0],
            "graph_edge": torchhd.random(1, dim, device=self.device)[0],
        }

        # Epistemic Boundaries
        self.threshold_consistency = threshold_consistency
        self.threshold_novelty = threshold_novelty  # Below this implies it is novel enough
        self.noise_tolerance = noise_tolerance  # Maximum acceptable noise/flip percentage

        # Cryptographic continuity
        self.ledger = MerkleLedger()

    def permute_temporal(self, hv: torch.Tensor, timestep: int) -> torch.Tensor:
        """Progressive permutation to encode time, yielding a natural similarity decay."""
        return F.permute(hv, shifts=timestep % 512)

    def encode_graph(self, nodes: list[torch.Tensor], edges: list[tuple[int, int]]) -> torch.Tensor:
        """Encodes a graph topology (nodes + edges) into a single Hypervector."""
        hv = torch.zeros(self.dim, device=self.device)

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

    def encode_episode(
        self, components: list[tuple[str, torch.Tensor]], timestep: int = 0
    ) -> torch.Tensor:
        """Encodes a full episodic event from components with temporal grounding."""
        hv = torch.zeros(self.dim, device=self.device)
        for role_name, filler in components:
            if role_name not in self.roles:
                self.roles[role_name] = torchhd.random(1, self.dim, device=self.device)[0]
            role = self.roles[role_name]

            bound = F.bind(role, filler)
            bound = self.permute_temporal(bound, timestep)
            hv = F.bundle(hv, bound)

        return F.normalize(hv)

    def _cleanup(self, hv: torch.Tensor) -> torch.Tensor:
        """Helper to cleanup a hypervector to its nearest neighbor in history."""
        if not self.history:
            return hv
        stack = torch.stack(self.history)
        sims = F.cosine_similarity(hv.unsqueeze(0), stack)
        best_idx = sims.argmax().item()
        return self.history[best_idx]

    def check_proposal(self, proposal_hv: torch.Tensor) -> dict:
        """
        Validates if a new proposal respects the epistemic boundary.
        Checks for consistency, novelty, and tamper/noise levels.
        """
        if not self.history:
            return {
                "accept": True,
                "reason": "first_commit",
                "confidence": 1.0,
                "max_similarity": 1.0,
            }

        # Query existing memory for similarity
        stack = torch.stack(self.history)
        sims = F.cosine_similarity(proposal_hv.unsqueeze(0), stack)

        max_sim = sims.max().item()
        avg_sim = sims.mean().item()
        best_idx = sims.argmax().item()

        consistency = max_sim >= self.threshold_consistency
        novelty = max_sim <= self.threshold_novelty

        # Tamper / noise detection via cleanup
        cleaned = self._cleanup(proposal_hv)
        noise_level = (
            1.0 - F.cosine_similarity(proposal_hv.unsqueeze(0), cleaned.unsqueeze(0)).item()
        )

        accept = consistency and novelty and noise_level < self.noise_tolerance

        return {
            "accept": accept,
            "max_similarity": max_sim,
            "avg_similarity": avg_sim,
            "noise_level": noise_level,
            "reason": "consistent_novel" if accept else "inconsistent_or_noisy",
            "nearest_index": best_idx,
            "suggestions": "refine_conflict"
            if not consistency
            else "increase_novelty"
            if not novelty
            else "reduce_noise",
        }

    def commit(
        self,
        proposal_hv: torch.Tensor,
        metadata: dict = None,  # type: ignore
        source_llm_hash: str = None,  # pyright: ignore[reportArgumentType]
    ) -> str:
        """
        Commits the proposal to the VSA memory and appends to the cryptographic ledger.
        """
        self.history.append(proposal_hv)
        if len(self.history) > self.max_history:
            self.history.pop(0)  # simple eviction

        # Add to Merkle Ledger
        membrane_result = metadata if metadata else {"max_similarity": 1.0, "accept": True}
        root_hash = self.ledger.append(proposal_hv, membrane_result, source_llm_hash)

        return root_hash

    def detect_and_mutate(
        self, recent_proposals: list[torch.Tensor], generations: int = 3
    ) -> tuple[torch.Tensor | None, dict | None]:
        """
        Autopoietic Mutation: Adjusts the epistemic membrane if global coherence drops.
        Generates a controlled mutant that anchors back to historical memory.
        """
        if not recent_proposals:
            return None, None

        global_hv = torch.zeros(self.dim, device=self.device)
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
                noise = torchhd.random(1, self.dim, device=self.device)[0] * 0.15
                mutation = F.bundle(mutation, noise)
                mutation = F.normalize(mutation)

            # Cleanup against historical memory to anchor the mutation
            cleaned = self._cleanup(mutation)
            return cleaned, {"mutation_type": "autopoietic_realignment", "old_coherence": coherence}

        return None, None
