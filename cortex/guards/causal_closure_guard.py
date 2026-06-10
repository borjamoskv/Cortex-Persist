# [C5-REAL] Exergy-Maximized
"""CORTEX - Causal Closure Guard (Axiom VIII: Stochastic Obsolescence).

Enforces the thermodynamic rule that massive probabilistic execution (e.g., Swarms)
MUST result in permanent structural condensation (C5-REAL invariants, code, schemas).
If a Swarm operation produces only prose/narrative without a deterministic artifact,
it is considered pure debt (Anergy) and is aborted via SAGA-1.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("cortex.guards.causal_closure")

@dataclass
class SwarmProposal:
    """Represents the output of a multi-agent or high-compute swarm execution."""
    agent_id: str
    mission_statement: str
    content: str
    token_cost: int = 0


class CausalClosureGuard:
    """Enforces Axiom VIII: Massive execution must yield deterministic artifacts."""

    def __init__(self, min_token_threshold: int = 50000):
        # Only enforce strictly if the swarm burned significant exergy
        self.min_token_threshold = min_token_threshold

    def _contains_structural_condensation(self, content: str) -> bool:
        """Detects if the content contains permanent structural artifacts."""
        # Look for code blocks indicating logic synthesis
        has_code_blocks = bool(re.search(r"```(?:python|yaml|json|diff|sql)", content, re.IGNORECASE))
        
        # Look for Ledger event payloads or Schema definitions
        has_ledger_payload = "LedgerPayload" in content or "CORTEX-TAINT" in content
        has_schema_update = "ALTER TABLE" in content or "CREATE TABLE" in content
        
        # Look for rigorous proof structures (Rule R2 format)
        has_formal_proof = bool(re.search(r"Proof:\s*\{.*Base:.*\}", content, re.IGNORECASE))
        
        return has_code_blocks or has_ledger_payload or has_schema_update or has_formal_proof

    def verify_closure(self, proposal: SwarmProposal) -> bool:
        """Evaluates if the swarm execution achieved causal closure.

        Args:
            proposal: The generated output from the swarm.

        Raises:
            RuntimeError: SAGA-1 Abort if the swarm failed to produce an invariant.

        Returns:
            bool: True if safe to persist.
        """
        if not proposal.content.strip():
            logger.warning("[%s] Empty proposal submitted.", proposal.agent_id)
            return False

        # If it's a cheap operation, we might not enforce strict causal closure
        if proposal.token_cost < self.min_token_threshold:
            logger.debug("[%s] Token cost below threshold, skipping causal closure guard.", proposal.agent_id)
            return True

        if not self._contains_structural_condensation(proposal.content):
            logger.error(
                "[%s] 🛑 [P0] Causal Closure Failure! "
                "Swarm execution burned %d tokens but produced no deterministic artifacts. "
                "Operation rejected as pure Anergy.",
                proposal.agent_id,
                proposal.token_cost
            )
            raise RuntimeError(
                f"[P0] AX-VIII Violation: Agent {proposal.agent_id} failed to achieve Causal Closure. "
                f"Swarm output must contain permanent invariants (code, ledger events, schemas) "
                f"after high-compute executions (Cost: {proposal.token_cost})."
            )

        logger.info("[%s] Causal Closure verified. Structural condensation detected.", proposal.agent_id)
        return True
