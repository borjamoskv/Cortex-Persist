"""
CORTEX V5 - Byzantine Consensus (LEGION-Ω)
Byzantine Fault Tolerance / Zero-Trust Mathematics: Axiom 4.
"""

import hashlib
import json
from typing import Any, Optional, TypeVar

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

    def evict_dead_nodes(self, min_reputation: float = 0.05) -> int:
        """Purge nodes whose reputation has been slashed below min_reputation."""
        dead = [nid for nid, n in self.nodes.items() if n.reputation < min_reputation]
        for nid in dead:
            del self.nodes[nid]
        return len(dead)

    def evict_stale_data(self) -> int:
        """Standard protocol eviction."""
        return self.evict_dead_nodes()

    def get_status(self) -> dict[str, Any]:
        return {"nodes_count": len(self.nodes)}

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

    async def execute_consensus(self, proposals: dict[str, T]) -> Optional[T]:
        """
        Takes proposals from multiple nodes. Validates them via reputation-weighted
        thresholding. Returns the absolute truth or None if BFT consensus fails.
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

        import math

        if math.isclose(total_reputation, 0.0, abs_tol=1e-9):
            return None

        # Find winning proposal
        winning_hash = max(vote_tally.keys(), key=lambda k: vote_tally[k])
        winning_weight = vote_tally[winning_hash]

        import math

        # Check against Byantine tolerance threshold
        ratio = winning_weight / total_reputation
        if ratio > self.tolerance_threshold or math.isclose(
            ratio, self.tolerance_threshold, rel_tol=1e-9
        ):
            # Consensus achieved
            await self._update_reputations(winning_hash, proposals)
            return hash_to_proposal[winning_hash]

        # Consensus failed (Shattered Trust)
        return None

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
