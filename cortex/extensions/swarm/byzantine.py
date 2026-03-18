"""
CORTEX V5 - Byzantine Consensus (LEGION-Ω)
Byzantine Fault Tolerance / Zero-Trust Mathematics: Axiom 4.
"""

import hashlib
import json
import logging
from typing import Any, TypeVar

logger = logging.getLogger("cortex.extensions.swarm.byzantine")


T = TypeVar("T")


class ByzantineNode:
    def __init__(self, node_id: str, reputation: float = 1.0):
        self.node_id = node_id
        self.reputation = reputation


class ByzantineConsensus:
    """
    Implements Zero-Trust consensus for multi-model / multi-agent swarms.
    Operates under the absolute premise that peripheral nodes hallucinate or lie.
    """

    def __init__(self, tolerance_threshold: float = 0.67):
        # By default, a 2/3 majority weighted by reputation is required.
        self.tolerance_threshold = tolerance_threshold
        self.nodes: dict[str, ByzantineNode] = {}

    def register_node(self, node_id: str, initial_reputation: float = 1.0) -> None:
        self.nodes[node_id] = ByzantineNode(node_id, initial_reputation)

    async def _get_proposal_hash(self, proposal: Any) -> str:
        """Deterministic hashing for any generic type via background thread."""
        import asyncio

        def _sync_hash() -> str:
            try:
                # Handle dicts/lists deterministically
                serialized = json.dumps(proposal, sort_keys=True, default=str)
            except (TypeError, ValueError):
                serialized = str(proposal)
            return hashlib.sha256(serialized.encode()).hexdigest()

        return await asyncio.to_thread(_sync_hash)

    async def execute_consensus(self, proposals: dict[str, T]) -> T | None:
        """
        Takes proposals from multiple nodes. Validates them via reputation-weighted
        thresholding and Ω-Consensus (Fracture Resonance).
        """
        if not proposals:
            return None

        vote_tally: dict[str, float] = {}
        hash_to_proposal: dict[str, T] = {}
        total_reputation = 0.0

        for node_id, proposal in proposals.items():
            if node_id not in self.nodes:
                continue

            rep = self.nodes[node_id].reputation
            total_reputation += rep

            proposal_hash = await self._get_proposal_hash(proposal)

            vote_tally[proposal_hash] = vote_tally.get(proposal_hash, 0.0) + rep
            hash_to_proposal[proposal_hash] = proposal

        if not total_reputation:
            return None

        # Find winning proposal
        winning_hash = max(vote_tally.keys(), key=lambda k: vote_tally[k])
        winning_weight = vote_tally[winning_hash]

        # Check against basic BFT threshold
        ratio = winning_weight / total_reputation
        if ratio < self.tolerance_threshold:
            return None

        # --- Ω∞: Article IV. Resonancia de Fractura (Inquisition) ---
        winning_proposal = hash_to_proposal[winning_hash]
        if not await self.fracture_inquisition(winning_proposal, proposals):
            logger.warning("⚔️ FRACTURE RESONANCE FAILED: Proposal did not survive the Inquisition (Ω-Consensus)")
            return None

        # Consensus achieved
        await self._update_reputations(winning_hash, proposals)
        return winning_proposal

    async def fracture_inquisition(self, winning_proposal: T, proposals: dict[str, T]) -> bool:
        """
        The Inquisition of Cortázar. A decision is legitimate ONLY if it survives 
        the dismantling attempt by the 1/3 most aggressive/dissenting nodes.
        """
        # 1. Identify dissenting voices (nodes not voting for winning proposal)
        # 2. If dissent weight > 0, we require a 'robustness' check.
        # For this Ω-impl, we simulate the 'survivability' by checking if 
        # thewinning proposal has high semantic density vs the noise.
        
        # Implementation: if winners have > 85% weight, they override fracture.
        # If winners are in 'shaky' territory (67-85%), even one strong dissent 
        # can trigger a Fracture Halt.
        
        vote_tally: dict[str, float] = {}
        total_rep = 0.0
        for nid, p in proposals.items():
            if nid not in self.nodes: continue
            rep = self.nodes[nid].reputation
            total_rep += rep
            phash = hashlib.sha256(str(p).encode()).hexdigest()
            vote_tally[phash] = vote_tally.get(phash, 0.0) + rep

        win_hash = hashlib.sha256(str(winning_proposal).encode()).hexdigest()
        win_ratio = vote_tally[win_hash] / total_rep
        
        if win_ratio > 0.85:
            return True # Absolute Resonance
            
        # Shaky territory: Check for a 'Critical Dissent' cluster (at least 1/6 total rep)
        # that provides a unified counter-proposal.
        dissent_hashes = [h for h in vote_tally if h != win_hash]
        for h in dissent_hashes:
            if vote_tally[h] / total_rep > 0.166: # 1/6th rule
                return False # Fractured Consensus
                
        return True


    async def _update_reputations(self, winning_hash: str, proposals: dict[str, T]) -> None:
        """
        Zero-trust reputation slashing. Nodes that hallucinated or Byzantine-lied
        lose reputation. Nodes that proposed the truth gain.
        """
        for node_id, proposal in proposals.items():
            if node_id not in self.nodes:
                continue

            proposal_hash = await self._get_proposal_hash(proposal)
            if proposal_hash == winning_hash:
                # Reward
                self.nodes[node_id].reputation = min(1.0, self.nodes[node_id].reputation * 1.05)
            else:
                # Slash
                self.nodes[node_id].reputation *= 0.8
