# [C5-REAL] Exergy-Maximized
"""
Epistemic Guard (L3.5)
Enforces the boundary rules between L4 Cognition and L3 Contracts.
Ensures no agent can forge an epistemic certainty level it is not entitled to.
"""

from typing import Any

from legacy_research.types.epistemics import (
    ConsensusNode,
    EpistemicNode,
    InferenceNode,
    ObservationNode,
)
from legacy_research.types.models import RejectionResult


class EpistemicGuard:
    """
    Validates Epistemic Nodes before they are admitted into the Sovereign State.
    """

    @classmethod
    def validate_node(cls, node: EpistemicNode, agent_role: str, context: dict[str, Any]) -> RejectionResult | None:
        """
        Validates an epistemic node against architectural invariants.
        Returns a RejectionResult if invalid, or None if valid.
        """
        if isinstance(node, ConsensusNode):
            # Only the WBFT routing layer or a Persist-Guardian can emit a ConsensusNode.
            if agent_role not in ["Persist-Guardian", "WBFT-Router"]:
                return {
                    "accepted": False,
                    "code": "EPISTEMIC_FORGERY",
                    "message": f"Agent role '{agent_role}' cannot emit a ConsensusNode.",
                    "layer": "guard",
                    "rule_id": "EG-001",
                    "severity": "critical",
                    "evidence": [{"node_type": "consensus", "agent_role": agent_role}],
                    "remediation": ["Route inference through WBFT consensus protocol instead of forging consensus."]
                }
            if len(node.voter_ids) < 3:
                return {
                    "accepted": False,
                    "code": "INVALID_QUORUM",
                    "message": f"ConsensusNode requires at least 3 voters, got {len(node.voter_ids)}.",
                    "layer": "guard",
                    "rule_id": "EG-002",
                    "severity": "high",
                    "evidence": [{"voter_count": len(node.voter_ids)}],
                    "remediation": ["Ensure WBFT quorum is met before emitting ConsensusNode."]
                }

        if isinstance(node, InferenceNode):
            if not node.source_node_ids:
                return {
                    "accepted": False,
                    "code": "ORPHAN_INFERENCE",
                    "message": "InferenceNode must declare causal predecessors (source_node_ids).",
                    "layer": "guard",
                    "rule_id": "EG-003",
                    "severity": "high",
                    "evidence": [{"source_node_ids": node.source_node_ids}],
                    "remediation": ["Provide source_node_ids from which this inference was derived."]
                }

        if isinstance(node, ObservationNode):
            if node.certainty not in ["C4", "C5"]:
                return {
                    "accepted": False,
                    "code": "INVALID_CERTAINTY",
                    "message": f"ObservationNode must have certainty C4 or C5, got {node.certainty}.",
                    "layer": "guard",
                    "rule_id": "EG-004",
                    "severity": "medium",
                    "evidence": [{"certainty": node.certainty}],
                    "remediation": ["Set certainty to C4 or C5 for direct observations."]
                }

        # Node is valid
        return None
