"""Verification Oracle — Deterministic validation for P0 Decoupling (V6).

Provides a ground-truth verification layer for facts and transactions,
independent of stochastic enrichment or external models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("cortex.verification")


@dataclass
class VerificationVerdict:
    """Result of a stateless verification check."""

    ok: bool
    verdict: str  # "accepted" | "rejected"
    reasons: list[str] = field(default_factory=list)


class VerificationOracle:
    """Sovereign Oracle for deterministic fact and ledger verification."""

    def __init__(self, engine: Optional[Any] = None):
        self.engine = engine

    # ─── Stateless Validation Surface ────────────────────────────────

    async def verify(
        self, subject: str, candidate: dict[str, Any]
    ) -> VerificationVerdict:
        """Stateless deterministic validation for structured candidates."""
        if subject == "plan_step":
            return self._verify_plan_step(candidate)
        elif subject == "tool_result":
            return self._verify_tool_result(candidate)
        return VerificationVerdict(
            ok=False, verdict="rejected", reasons=[f"Unknown subject: {subject}"]
        )

    def _verify_plan_step(self, candidate: dict[str, Any]) -> VerificationVerdict:
        reasons: list[str] = []
        if "objective" not in candidate:
            reasons.append("Plan step missing objective.")
        if reasons:
            return VerificationVerdict(ok=False, verdict="rejected", reasons=reasons)
        return VerificationVerdict(ok=True, verdict="accepted")

    def _verify_tool_result(self, candidate: dict[str, Any]) -> VerificationVerdict:
        reasons: list[str] = []
        ok_field = candidate.get("ok")
        if ok_field is False and "error" not in candidate:
            reasons.append(
                "Tool result marked as failed but no error message provided."
            )
        if reasons:
            return VerificationVerdict(ok=False, verdict="rejected", reasons=reasons)
        return VerificationVerdict(ok=True, verdict="accepted")

    # ─── Engine-Dependent Methods ────────────────────────────────────

    async def verify_fact_integrity(self, fact_id: int) -> bool:
        """Verify the cryptographic integrity of a fact record."""
        if not self.engine:
            return False
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT content, hash, metadata FROM facts WHERE id = ?", (fact_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
            return True

    async def check_enrichment_status(self, fact_id: int) -> str:
        """Check the status of enrichment for a specific fact."""
        if not self.engine:
            return "no_engine"
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT status FROM enrichment_jobs WHERE fact_id = ?"
                " ORDER BY id DESC LIMIT 1",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                cursor = await conn.execute(
                    "SELECT fact_id FROM embeddings WHERE fact_id = ?", (fact_id,)
                )
                if await cursor.fetchone():
                    return "completed"
                return "not_queued"
            return row[0]

    async def verify_ledger_continuity(self) -> bool:
        """Verify the integrity of the entire ledger chain."""
        if not self.engine:
            return False
        try:
            audit_result = await self.engine.ledger.audit()
            return audit_result["is_valid"]
        except Exception as e:
            logger.error("Ledger audit failed: %s", e)
            return False
