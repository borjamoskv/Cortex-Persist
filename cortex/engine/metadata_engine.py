"""CORTEX Metadata Engine — Deterministic and Async Classification.

Decouples metabolic state (Thermodynamic Plane) from thematic domain (Semantic Plane).
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.engine.models import Fact

logger = logging.getLogger("cortex.metadata")


class MetadataEngine:
    """Orchestrates fact classification across the Double-Plane architecture."""

    @staticmethod
    def classify_deterministic(fact: Fact) -> dict[str, Any]:
        """Immediate classification based on explicit cues (O(1)).
        Assigns default quadrant and category based on fact_type and content.
        """
        # Default metabolic state
        quadrant = "ACTIVE"
        storage_tier = "HOT"
        category = "general"
        yield_score = 1.0  # Initial default
        exergy_score = 1.0  # Initial default

        # ── Thermodynamic Rules ──
        if fact.fact_type in ("axiom", "invariant", "core_principle"):
            quadrant = "FOUNDATIONAL"
            exergy_score = 2.0  # High energy potential
        elif fact.fact_type in ("noise", "ephemeral", "debug"):
            quadrant = "NOISE"
            exergy_score = 0.1  # Low energy potential

        # Yield calculation based on confidence and content density
        conf_multiplier = {
            "C5": 1.5,
            "C4": 1.2,
            "C3": 1.0,
            "C2": 0.5,
            "C1": 0.2,
            "stated": 0.8,
        }.get(fact.confidence or "stated", 1.0)

        # content density (normalized log-ish)
        density_bonus = min(0.5, len(fact.content) / 1000.0)
        yield_score = 1.0 * conf_multiplier + density_bonus

        # ── Semantic Rules ──
        content_lower = fact.content.lower()
        if "auth" in content_lower or "login" in content_lower:
            category = "security"
        elif "cost" in content_lower or "price" in content_lower or "token" in content_lower:
            category = "economics"
        elif "test" in content_lower or "verify" in content_lower:
            category = "verification"

        # Tags influence category
        if "security" in fact.tags:
            category = "security"
        elif "performance" in fact.tags:
            category = "metabolism"
        elif "high-value" in fact.tags:
            exergy_score *= 1.5

        return {
            "category": category,
            "quadrant": quadrant,
            "storage_tier": storage_tier,
            "parent_id": fact.parent_id,
            "relation_type": fact.relation_type,
            "yield_score": round(yield_score, 2),
            "exergy_score": round(exergy_score, 2),
        }

    @staticmethod
    async def enrich_async(fact_id: int, content: str, engine: Any) -> dict[str, Any]:
        """Deep enrichment using LLM or intensive heuristics (Background)."""
        logger.debug("Enriching fact %d asynchronously", fact_id)

        # In a real implementation, this would call an LLM to:
        # 1. Refine the category (hierarchical semantic domain)
        # 2. Assign high-fidelity yield/exergy scores
        # 3. Detect contradictions with existing FOUNDATIONAL facts

        # Mocking enrichment for now
        return {
            "category": "refined",
            "yield_score": 1.5,
            "exergy_score": 0.8,
        }
