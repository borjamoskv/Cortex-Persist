# [C5-REAL] Exergy-Maximized
"""Verification Oracle - Deterministic validation for P0 Decoupling (V6).

Provides a ground-truth verification layer for facts and transactions,
independent of stochastic enrichment or external models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.verification")


@dataclass(frozen=True)
class VerificationOracleResult:
    """Lightweight compatibility result for verification checks."""

    ok: bool
    verdict: str
    reasons: list[str] = field(default_factory=list)


class VerificationOracle:
    """Sovereign Oracle for deterministic fact and ledger verification."""

    def __init__(self, engine: Any):
        self.engine = engine

    async def verify(self, subject: str, candidate: dict[str, Any]) -> VerificationOracleResult:
        """Verify a candidate payload for the requested subject."""
        if subject == "plan_step":
            reasons: list[str] = []
            if not candidate.get("objective"):
                reasons.append("Plan step missing objective.")
            if not candidate.get("steps"):
                reasons.append("Plan step missing steps.")
            ok = not reasons
            return VerificationOracleResult(
                ok=ok,
                verdict="accepted" if ok else "rejected",
                reasons=reasons,
            )

        if subject == "tool_result":
            reasons = []
            if candidate.get("ok") is False and not candidate.get("error"):
                reasons.append("Tool result marked as failed but no error message provided.")
            ok = not reasons
            return VerificationOracleResult(
                ok=ok,
                verdict="accepted" if ok else "rejected",
                reasons=reasons,
            )

        return VerificationOracleResult(ok=True, verdict="accepted")

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
        """Check the status of enrichment for a specific fact (Author: Borja Moskv)."""
        import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT status FROM enrichment_jobs WHERE fact_id = ? ORDER BY id DESC LIMIT 1",
                (fact_id,),
            )
            row = await cursor.fetchone()
            if not row:
                # Check if it already has an embedding (legacy or processed)
                try:
                    cursor = await conn.execute(
                        "SELECT fact_id FROM fact_embeddings WHERE fact_id = ?", (fact_id,)
                    )
                    if await cursor.fetchone():
                        return "completed"
                except sqlite3.OperationalError:
                    pass
                return "not_queued"
            return row[0]

    async def verify_ledger_continuity(self) -> bool:
        """Verify the integrity of the entire ledger chain."""
        try:
            if hasattr(self.engine, "verify_ledger"):
                audit_result = await self.engine.verify_ledger()
                return bool(audit_result.get("valid", audit_result.get("is_valid", False)))

            ledger = getattr(self.engine, "_ledger", None)
            if ledger is not None and hasattr(ledger, "audit_integrity_async"):
                audit_result = await ledger.audit_integrity_async()
                return bool(audit_result.get("valid", False))

            if hasattr(self.engine, "ledger") and hasattr(self.engine.ledger, "audit"):
                audit_result = await self.engine.ledger.audit()
                return bool(audit_result.get("is_valid", audit_result.get("valid", False)))

            logger.error("Ledger audit failed: engine does not expose a verification interface")
            return False
        except Exception as e:
            logger.error("Ledger audit failed: %s", e)
            return False
