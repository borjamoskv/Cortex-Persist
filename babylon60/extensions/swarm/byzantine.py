# [C5-REAL] Exergy-Maximized
"""
Byzantine Consensus (LEGION-Ω)
Byzantine Fault Tolerance / Zero-Trust Mathematics: Axiom 4.
"""

import asyncio
import json
import math
from typing import Any, TypeVar

from babylon60.crypto.hash_registry import cortex_hash

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

    @staticmethod
    def _normalize_proposal(proposal: Any) -> str:
        """Normalize proposal content using AST unparsing for code structures to achieve semantic consensus."""
        import ast

        if isinstance(proposal, str):
            try:
                tree = ast.parse(proposal)
                return ast.unparse(tree)
            except Exception:  # noqa: BLE001
                pass
        try:
            return json.dumps(proposal, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return str(proposal)

    @staticmethod
    def _hash_proposal(proposal: Any) -> str:
        """Deterministic SHA-256 hash of the normalized proposal."""
        normalized = ByzantineConsensus._normalize_proposal(proposal)
        return cortex_hash(normalized.encode())

    async def _get_proposal_hash(self, proposal: Any) -> str:
        """Hash a proposal in a background thread."""
        return await asyncio.to_thread(self._hash_proposal, proposal)

    async def _batch_hash_proposals(self, proposals: dict[str, Any]) -> dict[str, str]:
        """Hash all proposals concurrently (O(1) thread dispatch vs O(n))."""
        tasks = {
            nid: asyncio.to_thread(self._hash_proposal, prop)
            for nid, prop in proposals.items()
            if nid in self.nodes
        }
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results, strict=False))

    async def execute_consensus(
        self, proposals: dict[str, T], node_ids: list[str] | None = None
    ) -> T | None:
        """
        Takes proposals from multiple nodes. Validates them via reputation-weighted
        thresholding. Returns the absolute truth or None if BFT consensus fails.
        """
        if not proposals:
            return None

        if node_ids is None:
            participating_nodes = list(proposals.keys())
        else:
            participating_nodes = node_ids

        vote_tally: dict[str, float] = {}
        hash_to_proposal: dict[str, T] = {}

        # Batch hash only proposals from participating nodes
        filtered_proposals = {
            nid: prop for nid, prop in proposals.items() if nid in participating_nodes
        }
        node_hashes = await self._batch_hash_proposals(filtered_proposals)

        for node_id, proposal_hash in node_hashes.items():
            if node_id in self.nodes:
                rep = self.nodes[node_id].reputation
                vote_tally[proposal_hash] = vote_tally.get(proposal_hash, 0.0) + rep
                hash_to_proposal[proposal_hash] = proposals[node_id]

        total_reputation = sum(
            self.nodes[node_id].reputation
            for node_id in participating_nodes
            if node_id in self.nodes
        )

        if math.isclose(total_reputation, 0.0, abs_tol=1e-9) or not vote_tally:
            return None

        # Find winning proposal
        winning_hash = max(vote_tally.keys(), key=lambda k: vote_tally[k])
        winning_weight = vote_tally[winning_hash]

        # Check against Byzantine tolerance threshold
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
