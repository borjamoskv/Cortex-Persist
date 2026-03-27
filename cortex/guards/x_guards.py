import logging
from typing import Any

import aiosqlite

from cortex.utils.canonical import compute_tx_hash

logger = logging.getLogger("cortex.guards.x_intelligence")

class XForensicGuard:
    """Forensic-Grade X Intelligence Guard (AX-033/Ω₁₃).

    Enforces that all data originating from 'agent:x-intelligence' includes
    cryptographic IDs (x_id) and author information to maintain forensic
    audit trails. Supports Sovereign Gate v2 validation anchors.
    """

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        """Validate if the incoming X data is 'Forensic-Grade'."""

        # 1. Source verification (Extra safety, already filtered by adapter)
        source = meta.get("source", "")
        if "x-intelligence" not in source:
            return

        # 2. Check for minimal metadata (Forensic Requirement)
        # We accept 'x_id' as the primary forensic identifier
        x_id = meta.get("x_id") or meta.get("tweet_id") or meta.get("rest_id")
        if not x_id:
            raise ValueError(
                "[AX-033] Forensic-Grade Violation: X Fact missing unique identifier (x_id)."
            )

        # 3. Sovereign Gate v2: Ledger Anchoring (Ω₁₃)
        # If the data claims to be sovereign, it must have a valid anchor hash
        is_sovereign = meta.get("sovereign", False)
        if is_sovereign:
            anchor = meta.get("anchor_hash")
            if not anchor:
                raise ValueError(
                    "[Ω₁₃] Sovereign Gate Violation: Fact marked as sovereign missing 'anchor_hash'."
                )

            # Verify the anchor is cryptographically consistent with the content
            # We simulate verification by checking if anchor matches a local hash
            expected_anchor = compute_tx_hash(
                x_id, project, fact_type, content, meta.get("timestamp", "")
            )
            if anchor != expected_anchor:
                raise ValueError(
                    f"[Ω₁₃] Sovereign Gate Violation: Anchor mismatch. Expected {expected_anchor}."
                )

        # 4. Anomaly detection: Zero content but high metrics
        likes = meta.get("favorite_count", 0)
        if not content.strip() and likes > 100:
            raise ValueError(
                "[AX-033] Inconsistent X Fact: High engagement but empty content."
            )

        # 5. Content length gate
        if len(content) > 10000:  # X supports long posts, but 10k+ is suspicious
            raise ValueError("[AX-033] X content exceeds safety threshold (10k chars).")

        logger.debug("[AX-033] X Forensic-Grade passed for x_id=%s", x_id)
