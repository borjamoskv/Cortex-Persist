"""
CORTEX V7 - Metacognition & The Doubt Circuit (DOUBT-Ω)
Evaluates Semantic Divergence and Epistemic Uncertainty to prevent Coherence Traps.
Axiom Ω₃: Byzantine Default — Nothing is trusted by default, including consensus.
"""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel


class DoubtAlert(BaseModel):
    """Alert emitted when a Coherence Trap or high Epistemic Uncertainty is detected."""

    type: str  # "COHERENCE_TRAP" | "EPISTEMIC_DIVERGENCE" | "REPUTATION_SKEW"
    node_id: str
    severity: float  # 0.0 to 1.0
    reason: str
    suggested_action: str


class DoubtCircuit:
    """
    The Doubt Circuit (DOUBT-Ω).
    Monitors the semantic and reputational health of the Memory Graph.
    Identifies 'Coherence Traps' where agents reinforce each other without diversity.
    """

    def __init__(self, variance_threshold: float = 0.15, uncertainty_threshold: float = 0.4):
        self.variance_threshold = variance_threshold
        self.uncertainty_threshold = uncertainty_threshold

    def evaluate_node(self, node: Any, cluster_nodes: list[Any]) -> list[DoubtAlert]:
        """
        Evaluates a node against its semantic neighbors to detect anomalies.
        """
        alerts = []

        # 1. Detect Coherence Trap (High Reputation + Low Semantic Variance)
        # If all nodes in a cluster are identical and reputation is MAX, it's suspicious.
        variance = self._calculate_semantic_variance(node, cluster_nodes)
        reputation = getattr(node, "reputation_proof", 1.0)

        if variance < self.variance_threshold and reputation > 0.9:
            alerts.append(
                DoubtAlert(
                    type="COHERENCE_TRAP",
                    node_id=getattr(node, "node_id", "unknown"),
                    severity=0.8,
                    reason=f"Cluster variance ({variance:.4f}) below threshold with high reputation.",
                    suggested_action="Inject semantic noise or force re-evaluation by diverse agents.",
                )
            )

        # 2. Detect Epistemic Uncertainty (High Shannon Entropy in consolidation)
        # Based on how much "surprise" or contradiction the node encountered.
        entropy = getattr(node, "shannon_entropy", 0.0)
        if entropy > self.uncertainty_threshold:
            alerts.append(
                DoubtAlert(
                    type="EPISTEMIC_DIVERGENCE",
                    node_id=getattr(node, "node_id", "unknown"),
                    severity=entropy,
                    reason=f"High information entropy ({entropy:.4f}) detected in node.",
                    suggested_action="Delay maturation and trigger deep multi-modal verification.",
                )
            )

        return alerts

    def _calculate_semantic_variance(self, target_node: Any, neighbors: list[Any]) -> float:
        """
        Calculates the variance of embeddings in a local semantic neighborhood.
        Lower variance indicates higher consensus but potentially a coherence trap.
        """
        if not neighbors or len(neighbors) < 2:
            return 1.0  # Default to safe diversity

        target_emb = getattr(target_node, "embedding", None)
        if not target_emb:
            # Try dictionary access if it's not an object
            target_emb = target_node.get("embedding") if isinstance(target_node, dict) else None

        if not target_emb:
            return 1.0

        similarities = []
        for n in neighbors:
            n_emb = getattr(n, "embedding", None)
            if not n_emb and isinstance(n, dict):
                n_emb = n.get("embedding")

            if n_emb:
                sim = self._cosine_similarity(target_emb, n_emb)
                similarities.append(sim)

        if not similarities:
            return 1.0

        mean_sim = sum(similarities) / len(similarities)
        variance = sum((s - mean_sim) ** 2 for s in similarities) / len(similarities)
        return variance

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a < 1e-12 or norm_b < 1e-12:
            return 0.0
        return dot / (norm_a * norm_b)
