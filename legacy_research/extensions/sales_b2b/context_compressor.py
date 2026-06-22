# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - B2B Sales Context Compressor.

Applies Landauer's principle (thermodynamic context compression) to
automated messaging flows. To overcome context limits (Context Rot),
this module compresses long chains of emails, LinkedIn messages, or
historical context into strict structural invariants (JSON/YAML).

This prevents the LLM from processing zero-yield narrative "fluff"
and maximizes exergy by retaining only causal state transitions.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("cortex.extensions.sales_b2b.context_compressor")


class ContextCompressor:
    """Compresses conversational text into epistemic invariants."""

    def __init__(self, entropy_threshold: int = 4000) -> None:
        """
        Args:
            entropy_threshold: The number of characters
                at which the context is considered "rotting" and
                must be collapsed.
        """
        self.entropy_threshold = entropy_threshold

    def is_degraded(self, text: str) -> bool:
        """Evaluate if the text entropy exceeds the thermodynamic threshold."""
        return len(text) > self.entropy_threshold

    def compress_history(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Applies Landauer compression to an entire history array.
        Extracts structural facts and purges narrative fluff.
        
        Returns:
            A dictionary containing the state machine representation
            of the interaction, which can be safely injected into
            the Deep Research prompt.
        """
        logger.info("Applying thermodynamic context compression to %d messages.", len(history))
        
        # Simplified baseline for deterministic parsing
        invariants: dict[str, Any] = {
            "total_interactions": len(history),
            "last_contact_date": None,
            "extracted_objections": [],
            "extracted_needs": [],
            "current_stage": "UNKNOWN",
            "compression_hash": "",
        }
        
        # Ouroboros Exergy Hash calculation
        raw_dump = json.dumps(history, sort_keys=True).encode("utf-8")
        invariants["compression_hash"] = hashlib.sha256(raw_dump).hexdigest()[:16]

        if history:
            invariants["last_contact_date"] = history[-1].get("timestamp")
            
            # Simulated naive extraction for the causal baseline
            for msg in history:
                content = str(msg.get("content", "")).lower()
                if "budget" in content or "expensive" in content:
                    invariants["extracted_objections"].append("BUDGET")
                if "integration" in content or "api" in content:
                    invariants["extracted_needs"].append("INTEGRATION")
                    
        invariants["extracted_objections"] = sorted(list(set(invariants["extracted_objections"])))
        invariants["extracted_needs"] = sorted(list(set(invariants["extracted_needs"])))
        
        return invariants
