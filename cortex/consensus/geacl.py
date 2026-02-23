"""
CORTEX v5.2 — GEACL Coordinator (KETER-∞ Metal-Level).

GEACL (Gossip-Enabled Async Consensus Ledger) ties together:
1. WBFT (Weighted Byzantine Fault Tolerance) for LLM evaluation.
2. Gossip Protocol for P2P state synchronization.

When a node proposes a commit (e.g., code changes, tool calls),
the coordinator uses WBFT to determine the winning response. It then
creates a semantic digest of the intended action and propagates it via Gossip.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cortex.consensus.byzantine import ByzantineVerdict, WBFTConsensus
from cortex.ha.gossip import GossipProtocol
from cortex.thinking.fusion_models import ModelResponse, ThinkingHistory

__all__ = ["GEACLCoordinator", "GeaclCommitResult"]

logger = logging.getLogger("cortex.consensus.geacl")


@dataclass(slots=True)
class GeaclCommitResult:
    """Result of a GEACL commit proposal."""

    success: bool
    verdict: ByzantineVerdict
    action_digest: str | None
    domain: str


class GEACLCoordinator:
    """
    Coordinates local WBFT and P2P Gossip for consensus-backed actions.
    """

    def __init__(
        self,
        node_id: str,
        wbft: WBFTConsensus,
        gossip: GossipProtocol,
    ):
        self.node_id = node_id
        self.wbft = wbft
        self.gossip = gossip

    async def propose_commit(
        self,
        intent: str,
        domain: str,
        responses: list[ModelResponse],
        history: ThinkingHistory | None = None,
    ) -> GeaclCommitResult:
        """
        Evaluate LLM responses using WBFT and propagate the decision context via Gossip.

        Args:
            intent: Description of the intended action (e.g. "patch_db_writer").
            domain: The conceptual domain to apply model weights (e.g. "code").
            responses: The raw responses from the multi-model fusion.
            history: Historical win rates for reputation-weighted voting.

        Returns:
            GeaclCommitResult containing the verdict and propagation hash if successful.
        """
        logger.debug(
            "Node %s proposing GEACL commit for intent '%s' in domain '%s'",
            self.node_id,
            intent,
            domain,
        )

        # 1. Run local WBFT weighted by domain multipliers and historic reputation
        verdict = self.wbft.evaluate(responses, history=history, domain=domain)

        # If we didn't meet quorum or the confidence is too low, reject
        if not verdict.quorum_met or verdict.confidence < 0.5:
            logger.warning(
                "GEACL commit rejected: Quorum not met or confidence low (%.2f)",
                verdict.confidence,
            )
            return GeaclCommitResult(
                success=False,
                verdict=verdict,
                action_digest=None,
                domain=domain,
            )

        best_response = verdict.best_response()
        if not best_response:
            return GeaclCommitResult(
                success=False,
                verdict=verdict,
                action_digest=None,
                domain=domain,
            )

        # 2. Package the context as state and generate a semantic digest
        action_payload = {
            "intent": intent,
            "domain": domain,
            "best_model": best_response.label,
            "confidence": verdict.confidence,
            "content_hash": hash(best_response.content),  # Simplified for memory
        }

        # The state key represents this specific decision boundary
        state_key = f"geacl_commit_{intent}_{hash(intent)}"

        # 3. Propagate to Gossip anti-entropy protocol
        self.gossip.update_state(state_key, action_payload)

        # 4. Extract generated digest
        state_record = self.gossip.get_state(state_key)
        digest_hash = state_record.compute_hash() if state_record else None

        logger.info(
            "GEACL commit successful. Domain: %s, Confidence: %.2f, Hash: %s",
            domain,
            verdict.confidence,
            digest_hash,
        )

        return GeaclCommitResult(
            success=True,
            verdict=verdict,
            action_digest=digest_hash,
            domain=domain,
        )
