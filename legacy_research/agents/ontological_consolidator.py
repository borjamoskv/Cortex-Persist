# [C5-REAL] Exergy-Maximized
"""CORTEX Ontological Consolidator Agent (L3.5 Epistemic Layer).

Guards the Epistemic Dependency Graph (EDG) against 'epistemic mixing'.
Classifies and validates incoming facts into strict epistemic boundaries:
- OBSERVATION: Cryptographic provenance / sensor timestamp.
- INFERENCE: Causal parent references.
- SIMULATION/COUNTERFACTUAL: Sandbox isolation.
- CONSENSUS: Multi-agent or ZK signature.
"""

import enum
import hashlib
import logging
from typing import Any

from cortex.agents.base import ReactiveTaskAgent

logger = logging.getLogger("cortex.agents.ontological_consolidator")


class EpistemicClass(enum.Enum):
    OBSERVATION = "OBSERVATION"
    INFERENCE = "INFERENCE"
    SIMULATION = "SIMULATION"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    CONSENSUS = "CONSENSUS"


class OntologicalConsolidator(ReactiveTaskAgent):
    """
    Ontological Consolidator Agent Architecture.
    Validates node definitions, enforces formal constraints, and prevents
    epistemic mixing before state reaches the Master Ledger.
    """

    _SUPPORTED_OPS = frozenset(
        {"consolidate_node", "detect_epistemic_mixing", "propagate_invalidation"}
    )

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "consolidate_node":
            return await self._consolidate_node(payload)
        elif op == "detect_epistemic_mixing":
            return await self._detect_epistemic_mixing(payload)
        elif op == "propagate_invalidation":
            return await self._propagate_invalidation(payload)
        raise NotImplementedError(f"Op {op} not supported by OntologicalConsolidator")

    async def _consolidate_node(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Classify and validate an incoming node's epistemic integrity."""
        node_data = payload.get("node", {})
        raw_class = node_data.get("epistemic_class", "INFERENCE").upper()

        try:
            epistemic_class = EpistemicClass(raw_class)
        except ValueError:
            logger.error(f"[{self.agent_id}] Invalid epistemic class: {raw_class}")
            return {"status": "REJECTED", "reason": "Invalid EpistemicClass"}

        validation_result = self._validate_constraints(epistemic_class, node_data)

        if not validation_result["is_valid"]:
            logger.warning(f"[{self.agent_id}] Epistemic violation: {validation_result['reason']}")
            return {"status": "REJECTED", "reason": validation_result["reason"]}

        # Construct deterministic EDG node signature
        node_hash = self._generate_node_hash(node_data)

        return {
            "status": "CONSOLIDATED",
            "epistemic_class": epistemic_class.value,
            "node_hash": node_hash,
            "confidence_score": validation_result["confidence_score"],
        }

    def _validate_constraints(
        self, e_class: EpistemicClass, node: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply zero-entropy deterministic constraints based on epistemic class."""
        if e_class == EpistemicClass.OBSERVATION:
            if "provenance_hash" not in node and "sensor_timestamp" not in node:
                return {
                    "is_valid": False,
                    "reason": "OBSERVATION lacks physical/cryptographic provenance.",
                }
            return {"is_valid": True, "confidence_score": 100}

        elif e_class == EpistemicClass.INFERENCE:
            parents = node.get("causal_parents", [])
            if not isinstance(parents, list) or len(parents) == 0:
                return {
                    "is_valid": False,
                    "reason": "INFERENCE must have explicitly declared causal parents.",
                }
            # Confidence is derived; placeholder for causal decay logic
            return {"is_valid": True, "confidence_score": node.get("confidence_score", 50)}

        elif e_class in (EpistemicClass.SIMULATION, EpistemicClass.COUNTERFACTUAL):
            if "sandbox_id" not in node:
                return {
                    "is_valid": False,
                    "reason": "SIMULATION/COUNTERFACTUAL must run in isolated sandbox context.",
                }
            return {"is_valid": True, "confidence_score": 0}  # No reality bearing

        elif e_class == EpistemicClass.CONSENSUS:
            signatures = node.get("signatures", [])
            if len(signatures) < 3:
                return {"is_valid": False, "reason": "CONSENSUS requires minimum Quorum (N=3)."}
            return {"is_valid": True, "confidence_score": 100}

        return {"is_valid": False, "reason": "Unhandled epistemic class"}

    async def _detect_epistemic_mixing(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyzes a sub-graph to ensure deterministic isolation between layers.
        For example, preventing an INFERENCE from being injected into an OBSERVATION trace.
        """
        nodes = payload.get("nodes", [])
        violations = []

        for idx, node in enumerate(nodes):
            e_class = node.get("epistemic_class")
            parents = node.get("causal_parents_classes", [])

            # An OBSERVATION cannot have an INFERENCE as a parent.
            if e_class == "OBSERVATION" and "INFERENCE" in parents:
                violations.append(
                    f"Node {idx}: Epistemic mixing detected. OBSERVATION cannot stem from INFERENCE."
                )

            # A CONSENSUS node must trace back to verifiable inputs.
            if e_class == "CONSENSUS" and "SIMULATION" in parents:
                violations.append(f"Node {idx}: SIMULATION cannot directly dictate CONSENSUS.")

        is_clean = len(violations) == 0
        return {"is_clean": is_clean, "violations": violations}

    def _generate_node_hash(self, node: dict[str, Any]) -> str:
        """Deterministically hash the structural content of the node."""
        content = str(node.get("content", ""))
        e_class = str(node.get("epistemic_class", ""))
        raw = f"{e_class}:{content}".encode()
        return hashlib.sha256(raw).hexdigest()

    async def _propagate_invalidation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Calculates the blast radius of an invalidated base node.
        If an OBSERVATION is revoked, all INFERENCE nodes that causally
        depend on it must have their confidence score collapsed to 0.
        """
        invalidated_node_id = payload.get("invalidated_node_id")
        edg_subgraph = payload.get("edg_subgraph", [])  # Flattened dependencies

        collapsed_nodes = []
        for node in edg_subgraph:
            parents = node.get("causal_parents", [])
            if invalidated_node_id in parents:
                node["confidence_score"] = 0
                node["status"] = "INVALIDATED"
                collapsed_nodes.append(node.get("node_id", "unknown"))

        logger.info(
            f"[{self.agent_id}] Propagated invalidation from {invalidated_node_id}. Collapsed {len(collapsed_nodes)} nodes."
        )

        return {
            "status": "PROPAGATION_COMPLETE",
            "invalidated_root": invalidated_node_id,
            "collapsed_nodes": collapsed_nodes,
        }
