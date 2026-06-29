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

from babylon60.guards.structural_certifier import StructuralCertifier, StructuralGrade

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
        # Check if the content is a serialized LedgerPayload
        inner_contents = [content]

        try:
            import json

            parsed = json.loads(content)
            if isinstance(parsed, dict):
                # If it's a LedgerPayload wrapper, inspect the actual inner payloads
                if parsed.get("type") == "LedgerPayload" and "payloads" in parsed:
                    inner_contents = []
                    for p in parsed["payloads"]:
                        if isinstance(p, dict):
                            # Extract all string values from the dictionary payload
                            inner_contents.extend(str(v) for v in p.values() if isinstance(v, str))
                        elif isinstance(p, str):
                            inner_contents.append(p)
        except (ValueError, TypeError, KeyError, AssertionError):
            pass

        for c in inner_contents:
            # Look for code blocks indicating logic synthesis
            has_code_blocks = bool(re.search(r"```\w*", c, re.IGNORECASE))

            # Look for Ledger event payloads or Schema definitions
            # Check for CORTEX-TAINT in the payload, or LedgerPayload in actual payload text
            has_ledger_payload = "CORTEX-TAINT" in c or ("LedgerPayload" in c and c != content)
            has_schema_update = "ALTER TABLE" in c or "CREATE TABLE" in c

            # Look for rigorous proof structures (Rule R2 format)
            has_formal_proof = bool(re.search(r"Proof:\s*\{.*Base:.*\}", c, re.IGNORECASE))

            # Detect a plain JSON-array of dicts
            has_json_array = False
            stripped_c = c.strip()
            if stripped_c.startswith("[") and stripped_c.endswith("]"):
                try:
                    parsed_arr = json.loads(stripped_c)
                    if (
                        isinstance(parsed_arr, list)
                        and all(isinstance(x, dict) for x in parsed_arr)
                        and len(parsed_arr) > 0
                    ):
                        has_json_array = True
                except json.JSONDecodeError:
                    try:
                        import ast

                        parsed_arr = ast.literal_eval(stripped_c)
                        if (
                            isinstance(parsed_arr, list)
                            and all(isinstance(x, dict) for x in parsed_arr)
                            and len(parsed_arr) > 0
                        ):
                            has_json_array = True
                    except (ValueError, SyntaxError, TypeError):
                        pass

            # Use StructuralCertifier to validate formal JSON structure
            grade = StructuralCertifier.certify_structure(c)
            has_valid_structure = grade == StructuralGrade.ACCEPTED

            if (
                has_code_blocks
                or has_ledger_payload
                or has_schema_update
                or has_formal_proof
                or has_json_array
                or has_valid_structure
            ):
                return True

        return False

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

        if not self._contains_structural_condensation(proposal.content):
            logger.error(
                "[%s] 🛑 [P0] Causal Closure Failure! "
                "Swarm execution burned %d tokens but produced no deterministic artifacts. "
                "Operation rejected as pure Anergy.",
                proposal.agent_id,
                proposal.token_cost,
            )
            raise RuntimeError(
                f"[P0] AX-VIII Violation: Agent {proposal.agent_id} failed to achieve Causal Closure. "
                f"Swarm output must contain permanent invariants (code, ledger events, schemas) "
                f"after high-compute executions (Cost: {proposal.token_cost})."
            )

        logger.info(
            "[%s] Causal Closure verified. Structural condensation detected.", proposal.agent_id
        )
        return True
