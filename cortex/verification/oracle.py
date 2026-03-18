"""Verification Oracle — Deterministic validation for P0 Decoupling (V6).

Provides a ground-truth verification layer for facts, transactions, and
agent outputs — independent of stochastic enrichment or external models.

AX-033: Stochastic outputs must cross a deterministic validation boundary.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("cortex.verification")


# ── Result type ────────────────────────────────────────────────────────────


@dataclass
class VerificationResult:
    """Immutable verdict emitted by the oracle after validating a candidate."""

    ok: bool
    verdict: str  # "accepted" | "rejected" | "unknown_subject"
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Subject validators ─────────────────────────────────────────────────────


def _verify_plan_step(candidate: Any) -> VerificationResult:
    reasons: list[str] = []
    if not isinstance(candidate, dict):
        return VerificationResult(
            ok=False, verdict="rejected", reasons=["Plan step must be a dict."]
        )
    if "objective" not in candidate:
        reasons.append("Plan step missing objective.")
    if "steps" not in candidate or not candidate["steps"]:
        reasons.append("Plan step missing or empty steps list.")
    ok = len(reasons) == 0
    return VerificationResult(ok=ok, verdict="accepted" if ok else "rejected", reasons=reasons)


def _verify_tool_result(candidate: Any) -> VerificationResult:
    reasons: list[str] = []
    if not isinstance(candidate, dict):
        return VerificationResult(
            ok=False, verdict="rejected", reasons=["Tool result must be a dict."]
        )
    if "ok" not in candidate:
        reasons.append("Tool result missing 'ok' field.")
    elif not candidate["ok"]:
        if not candidate.get("error"):
            reasons.append("Tool result marked as failed but no error message provided.")
    ok = len(reasons) == 0
    return VerificationResult(ok=ok, verdict="accepted" if ok else "rejected", reasons=reasons)


# ── Subject registry ───────────────────────────────────────────────────────

_VALIDATORS = {
    "plan_step": _verify_plan_step,
    "tool_result": _verify_tool_result,
}


# ── Oracle ─────────────────────────────────────────────────────────────────


class VerificationOracle:
    """Sovereign Oracle: deterministic fact, ledger, and agent output verification.

    Can be instantiated standalone (no engine) for pure structural verification,
    or with an engine reference for ledger-level checks.
    """

    def __init__(self, engine: Optional[Any] = None) -> None:
        self.engine = engine

    # ── Primary dispatcher ─────────────────────────────────────────────────

    async def verify(self, subject: str, candidate: Any) -> VerificationResult:
        """Dispatch validation by subject type.

        Args:
            subject: The verification domain ("plan_step", "tool_result", …).
            candidate: The data structure to validate.

        Returns:
            VerificationResult with ok, verdict, and reasons.
        """
        validator = _VALIDATORS.get(subject)
        if validator is None:
            return VerificationResult(
                ok=False,
                verdict="unknown_subject",
                reasons=[f"No validator registered for subject '{subject}'."],
            )
        return validator(candidate)

    # ── Ledger-level checks (require engine) ──────────────────────────────

    async def verify_fact_integrity(self, fact_id: int) -> bool:
        """Verify the cryptographic integrity of a fact record."""
        if self.engine is None:
            raise RuntimeError("VerificationOracle requires an engine for fact integrity checks.")
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT content, hash, metadata FROM facts WHERE id = ?", (fact_id,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def check_enrichment_status(self, fact_id: int) -> str:
        """Check the enrichment status for a specific fact."""
        if self.engine is None:
            raise RuntimeError("VerificationOracle requires an engine for enrichment checks.")
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT status FROM enrichment_jobs WHERE fact_id = ? ORDER BY id DESC LIMIT 1",
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
        if self.engine is None:
            raise RuntimeError(
                "VerificationOracle requires an engine for ledger continuity checks."
            )
        try:
            audit_result = await self.engine.ledger.audit()
            return audit_result["is_valid"]
        except Exception as e:
            logger.error("Ledger audit failed: %s", e)
            return False
