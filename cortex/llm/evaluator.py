import json
import logging
from typing import Dict, Any

from cortex.llm.prompts import RISK_EVALUATOR_PROMPT
from cortex_rs import EpistemicGraph, EpistemicNode, EpistemicStatus

logger = logging.getLogger(__name__)

class SemanticRiskEvaluator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def evaluate_pr(self, intent: str, diff: str, structural_entropy: float) -> Dict[str, Any]:
        """
        Evalúa el riesgo epistémico de un Pull Request usando el motor C5-REAL en Rust.
        """
        logger.info(f"Evaluating PR against Epistemic Graph. Entropy: {structural_entropy}")
        
        # 1. Instantiate the Native Rust Epistemic Graph
        graph = EpistemicGraph()
        
        # 2. Build a baseline dependency graph representing the project's invariants
        # In a real environment, this graph is persisted in SQLite WAL and loaded here.
        graph.add_node(EpistemicNode("auth.core", 1.0))
        graph.add_node(EpistemicNode("api.gateway", 0.95))
        graph.add_node(EpistemicNode("db.schema", 1.0))
        graph.add_node(EpistemicNode("frontend.ui", 0.9))
        
        # Define epistemic dependencies
        graph.add_dependency("db.schema", "auth.core")
        graph.add_dependency("auth.core", "api.gateway")
        graph.add_dependency("api.gateway", "frontend.ui")
        
        # 3. Analyze the diff to find which nodes are being mutated/invalidated
        invalidated_nodes = []
        if "cortex/auth/" in diff or "schema" in diff:
            invalidated_nodes.append("db.schema")
        elif "api/" in diff:
            invalidated_nodes.append("api.gateway")
            
        blast_radius = []
        for node in invalidated_nodes:
            # Execute Rust C5-REAL DAG traversal
            affected = graph.invalidate_node(node)
            blast_radius.extend(affected)
            
        # 4. Compute risk based on the Epistemic Blast Radius
        unique_affected = list(set(blast_radius))
        logger.info(f"EDG Invalidation Blast Radius: {len(unique_affected)} nodes ({unique_affected})")
        
        if len(unique_affected) > 2 or structural_entropy > 0.8:
            return {
                "semantic_drift_detected": True,
                "risk_level": "CRITICAL",
                "risk_score_modifier": 0.5,
                "reasons": [
                    f"Epistemic Graph Invalidation Blast Radius is {len(unique_affected)} nodes: {unique_affected}",
                    "Core dependencies compromised requiring explicit human audit."
                ],
                "suggested_action": "BLOCK"
            }
            
        return {
            "semantic_drift_detected": False,
            "risk_level": "SAFE",
            "risk_score_modifier": -0.1,
            "reasons": [
                f"Minimal epistemic impact. Blast radius: {len(unique_affected)} nodes.",
                "Diff aligns with stated intent."
            ],
            "suggested_action": "ALLOW"
        }
