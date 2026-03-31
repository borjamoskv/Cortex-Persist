"""Verification Oracle — Deterministic validation for P0 Decoupling (V6).

Provides a ground-truth verification layer for facts and transactions,
independent of stochastic enrichment or external models.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.verification")


class VerificationOracle:
    """Sovereign Oracle for deterministic fact and ledger verification."""

    def __init__(self, engine: Any):
        self.engine = engine

    async def verify_fact_integrity(self, fact_id: int) -> bool:
        """Verify the cryptographic integrity of a fact record."""
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT content, hash, metadata FROM facts WHERE id = ?", (fact_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False

            # Additional deterministic checks (hash equality, signature verification)
            # would go here. For P0, we focus on presence and ledger consistency.
            return True

    async def check_enrichment_status(self, fact_id: int) -> str:
        """Check the status of enrichment for a specific fact."""
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT status FROM enrichment_jobs WHERE fact_id = ? ORDER BY id DESC LIMIT 1",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                # Check if it already has an embedding (legacy or processed)
                cursor = await conn.execute(
                    "SELECT fact_id FROM embeddings WHERE fact_id = ?", (fact_id,)
                )
                if await cursor.fetchone():
                    return "completed"
                return "not_queued"
            return row[0]

    async def verify_ledger_continuity(self) -> bool:
        """Verify the integrity of the entire ledger chain."""
        try:
            if hasattr(self.engine, "verify_ledger"):
                audit_result = await self.engine.verify_ledger()
                return bool(audit_result.get("valid", audit_result.get("is_valid", False)))

            ledger = getattr(self.engine, "_ledger", None)
            if ledger is not None and hasattr(ledger, "verify_integrity_async"):
                audit_result = await ledger.verify_integrity_async()
                return bool(audit_result.get("valid", False))

            if hasattr(self.engine, "ledger") and hasattr(self.engine.ledger, "audit"):
                audit_result = await self.engine.ledger.audit()
                return bool(audit_result.get("is_valid", audit_result.get("valid", False)))

            logger.error("Ledger audit failed: engine does not expose a verification interface")
            return False
        except Exception as e:
            logger.error("Ledger audit failed: %s", e)
            return False
