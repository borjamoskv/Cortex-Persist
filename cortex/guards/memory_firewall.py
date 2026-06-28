# [C5-REAL] Exergy-Maximized
"""
CORTEX - Memory Firewall Guard (H3.1).

Enforces epistemic containment before facts are allowed to mutate the
persistent state. Evaluates the `CORTEX-TAINT` signature, confidence
thresholds, and prevents hallucinated or stochastic outputs from entering
the memory substrate.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.crypto.keys import ZKSwarmIdentity

logger = logging.getLogger("cortex.guards.memory_firewall")


class MemoryFirewallGuard:
    """Intercepts memory writes to enforce strict epistemic boundaries.

    Part of the Write-Path SAGA Contract (Step 1).
    """

    def __init__(self, require_taint: bool = True, min_confidence: str = "C3"):
        self.require_taint = require_taint
        self.min_confidence = min_confidence

        # C1 to C5 ranking for threshold comparison
        self._confidence_rank = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5, "STATED": 3}

    def validate_fact(
        self, content: str, source: str, confidence: str, meta: dict[str, Any] | None = None
    ) -> bool:
        """
        Validates an incoming fact proposal before persistence.

        Args:
            content: The text content of the fact.
            source: The agent_id or origin of the fact.
            confidence: Epistemic confidence (e.g., "C3", "C5-REAL").
            meta: Metadata dictionary which should contain 'CORTEX-TAINT'.

        Raises:
            ValueError: If the fact is rejected by the firewall.

        Returns:
            True if valid and allowed into memory.
        """
        if not content.strip():
            raise ValueError("[P0] Memory Firewall: Cannot persist empty fact.")

        meta = meta or {}

        # 1. Epistemic Confidence Check
        clean_conf = confidence.split("-")[0].upper()
        if clean_conf in self._confidence_rank:
            min_rank = self._confidence_rank.get(self.min_confidence, 3)
            current_rank = self._confidence_rank[clean_conf]
            if current_rank < min_rank:
                raise ValueError(
                    f"[P0] Memory Firewall: Fact confidence '{confidence}' is below minimum threshold '{self.min_confidence}'."
                )
        else:
            raise ValueError(f"[P0] Memory Firewall: Invalid confidence level '{confidence}'.")

        # 2. Taint Verification (CORTEX-TAINT)
        if self.require_taint:
            taint = (
                meta.get("CORTEX-TAINT")
                or meta.get("cortex_taint")
                or meta.get("cortex-taint")
                or meta.get("CORTEX_TAINT")
            )
            if not taint:
                raise ValueError(
                    f"[P0] Memory Firewall: Fact from source '{source}' lacks CORTEX-TAINT. "
                    "All persistent state mutations must carry cryptographic attribution."
                )

            # taint format: taint:{agent_id}:{session_id}:{timestamp}:{signature_b64}
            parts = taint.split(":")
            if len(parts) >= 5 and parts[0] == "taint":
                signature_b64 = parts[-1]
                public_key_b64 = meta.get("agent_public_key")

                # If we have the public key, verify the signature
                if public_key_b64:
                    is_valid = ZKSwarmIdentity.verify_payload(
                        content, public_key_b64, signature_b64
                    )
                    if not is_valid:
                        raise ValueError(
                            "[P0] Memory Firewall: CORTEX-TAINT signature verification failed."
                        )
            else:
                logger.warning("Malformed CORTEX-TAINT metadata: %s", taint)

        logger.debug("Memory Firewall cleared fact from %s", source)
        return True
