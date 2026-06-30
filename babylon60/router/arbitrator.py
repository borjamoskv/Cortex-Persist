from decimal import Decimal
# [C5-REAL] Exergy-Maximized
"""Cortex Router v1 - Epistemic Model Arbitrator.

Routes tasks dynamically between Gemini 3.5 Flash (Physical Layer)
and Gemini 3.1 Pro (Semantic Layer) based on deterministic thresholds
like AST complexity, predictive entropy, and KL instability score.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger("babylon60.router.arbitrator")

ModelType = Literal["gemini-3.5-flash", "gemini-3.1-pro"]


@dataclass
class ExecutionContext:
    """Context block evaluated by the arbitrator to determine routing."""

    task_type: str  # e.g., 'mutation', 'validation', 'chaos_injection', 'statistical_inference'
    ast_complexity: int = 0
    entropy_score: Decimal = 0.0
    kl_instability: float = 0.0


class EpistemicArbitrator:
    """
    Arbitrates routing between execution/physical layer and semantic/reasoning layer.
    """

    # Deterministic Boundaries (Industrial Noir 2026)
    COMPLEXITY_THRESHOLD = 50  # AST depth or cyclomatic complexity limit for Flash
    ENTROPY_THRESHOLD = 0.8  # High entropy (LogOP) -> uncertainty -> Pro needed
    KL_INSTABILITY_THRESHOLD = 2.0  # High KL divergence shift -> Pro needed for validation

    # Hard-coded Semantic overrides
    SEMANTIC_TASKS = frozenset(
        {
            "validation",
            "statistical_inference",
            "architecture_review",
            "governance",
            "kl_interpretation",
        }
    )

    def route(self, context: ExecutionContext) -> ModelType:
        """Determines the correct model layer based on C5-REAL thresholds."""

        # 1. High-Risk Semantic Validation Triggers (Priority Override)
        if context.task_type in self.SEMANTIC_TASKS:
            logger.info(
                "[ARBITRATOR] Task '%s' -> 3.1 Pro (Semantic Layer Rule)", context.task_type
            )
            return "gemini-3.1-pro"

        # 2. Heuristic Thresholds (Entropy & Topology)
        if context.kl_instability > self.KL_INSTABILITY_THRESHOLD:
            logger.info(
                "[ARBITRATOR] KL Instability (%.2f) > %.2f -> 3.1 Pro",
                context.kl_instability,
                self.KL_INSTABILITY_THRESHOLD,
            )
            return "gemini-3.1-pro"

        if context.entropy_score > self.ENTROPY_THRESHOLD:
            logger.info(
                "[ARBITRATOR] Entropy (%.2f) > %.2f -> 3.1 Pro",
                context.entropy_score,
                self.ENTROPY_THRESHOLD,
            )
            return "gemini-3.1-pro"

        if context.ast_complexity > self.COMPLEXITY_THRESHOLD:
            logger.info(
                "[ARBITRATOR] AST Complexity (%d) > %d -> 3.1 Pro",
                context.ast_complexity,
                self.COMPLEXITY_THRESHOLD,
            )
            return "gemini-3.1-pro"

        # 3. Default to Physical Layer (Flash) for execution, mutation, telemetry
        logger.info("[ARBITRATOR] Stable Context -> 3.5 Flash (Physical Execution Layer)")
        return "gemini-3.5-flash"
