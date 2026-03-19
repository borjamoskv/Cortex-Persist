"""Verification Oracle — Deterministic trust boundary for P0 Decoupling (V7).

Provides a ground-truth verification layer for facts and the ledger chain,
independent of stochastic enrichment or external models.

Axiom Ω₃ (Byzantine Default):
    SHA-256 recomputed live. NULL hash is a violation, not a skip.
    Silence is NOT compliance.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.verification.oracle")


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactIntegrityResult:
    """Cryptographic verification outcome for a single fact."""

    fact_id: int
    valid: bool
    violation: str | None = None
    project: str | None = None


@dataclass(frozen=True)
class EnrichmentStatus:
    """Enrichment pipeline status for a fact."""

    fact_id: int
    status: str  # "completed" | "pending" | "failed" | "not_queued"


@dataclass(frozen=True)
class LedgerContinuityResult:
    """Full chain verification outcome."""

    valid: bool
    checked_events: int
    violations: list[str]


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------


class VerificationOracle:
    """Sovereign Oracle for deterministic fact and ledger verification.

    V7 — Ω₃ Byzantine Gate applied throughout:
      • verify_fact_integrity: live SHA-256 recomputation (no trust in stored state).
      • verify_fact_batch:     O(N) single-pass batch verification.
      • check_enrichment_status: enrichment pipeline probe.
      • verify_ledger_continuity: delegates to LedgerVerifier chain audit.
    """

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    # ------------------------------------------------------------------
    # Single-fact verification
    # ------------------------------------------------------------------

    async def verify_fact_integrity(self, fact_id: int) -> FactIntegrityResult:
        """Verify cryptographic integrity of a single fact.

        Recomputes SHA-256(content) and compares against stored hash.
        Returns a VIOLATION for NULL hash or empty content — not a skip.
        """
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT content, hash, project FROM facts WHERE id = ?",
                (fact_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return FactIntegrityResult(
                fact_id=fact_id,
                valid=False,
                violation=f"FACT_NOT_FOUND — id={fact_id}",
            )

        content: str = row[0] or ""
        stored_hash: str = row[1] or ""
        project: str | None = row[2]

        if not content:
            return FactIntegrityResult(
                fact_id=fact_id,
                valid=False,
                violation="EMPTY_CONTENT — Cannot verify integrity of empty fact.",
                project=project,
            )

        if not stored_hash:
            return FactIntegrityResult(
                fact_id=fact_id,
                valid=False,
                violation="NULL_HASH — Fact was never signed. Chain trust invalidated.",
                project=project,
            )

        recomputed = hashlib.sha256(content.encode()).hexdigest()

        if recomputed != stored_hash:
            logger.warning(
                "⚠️ [ORACLE] Fact #%d hash mismatch (project=%s). stored=%s… recomputed=%s…",
                fact_id,
                project,
                stored_hash[:16],
                recomputed[:16],
            )
            return FactIntegrityResult(
                fact_id=fact_id,
                valid=False,
                violation=(
                    f"HASH_MISMATCH — stored={stored_hash[:16]}… recomputed={recomputed[:16]}…"
                ),
                project=project,
            )

        return FactIntegrityResult(fact_id=fact_id, valid=True, project=project)

    # ------------------------------------------------------------------
    # Batch verification — O(N) single-pass
    # ------------------------------------------------------------------

    async def verify_fact_batch(
        self,
        fact_ids: list[int] | None = None,
        *,
        limit: int = 500,
    ) -> list[FactIntegrityResult]:
        """Verify multiple facts in a single DB round-trip.

        If *fact_ids* is None, verifies the most recent *limit* facts.
        Significantly faster than calling verify_fact_integrity in a loop.
        """
        async with self.engine.session() as conn:
            if fact_ids:
                placeholders = ",".join("?" * len(fact_ids))
                cursor = await conn.execute(
                    f"SELECT id, content, hash, project FROM facts WHERE id IN ({placeholders})",
                    fact_ids,
                )
            else:
                cursor = await conn.execute(
                    "SELECT id, content, hash, project FROM facts ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            rows = await cursor.fetchall()

        results: list[FactIntegrityResult] = []

        for row in rows:
            fid: int = row[0]
            content: str = row[1] or ""
            stored_hash: str = row[2] or ""
            project: str | None = row[3]

            if not content:
                results.append(
                    FactIntegrityResult(
                        fact_id=fid, valid=False, violation="EMPTY_CONTENT", project=project
                    )
                )
                continue

            if not stored_hash:
                results.append(
                    FactIntegrityResult(
                        fact_id=fid, valid=False, violation="NULL_HASH", project=project
                    )
                )
                continue

            recomputed = hashlib.sha256(content.encode()).hexdigest()
            if recomputed != stored_hash:
                results.append(
                    FactIntegrityResult(
                        fact_id=fid,
                        valid=False,
                        violation=f"HASH_MISMATCH — stored={stored_hash[:16]}…",
                        project=project,
                    )
                )
            else:
                results.append(FactIntegrityResult(fact_id=fid, valid=True, project=project))

        return results

    # ------------------------------------------------------------------
    # Enrichment status
    # ------------------------------------------------------------------

    async def check_enrichment_status(self, fact_id: int) -> EnrichmentStatus:
        """Probe the enrichment pipeline status for a fact."""
        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT status FROM enrichment_jobs WHERE fact_id = ? ORDER BY id DESC LIMIT 1",
                (fact_id,),
            )
            row = await cursor.fetchone()

            if not row:
                # Check if embedding already exists (processed externally)
                cursor = await conn.execute(
                    "SELECT fact_id FROM embeddings WHERE fact_id = ?",
                    (fact_id,),
                )
                if await cursor.fetchone():
                    return EnrichmentStatus(fact_id=fact_id, status="completed")
                return EnrichmentStatus(fact_id=fact_id, status="not_queued")

        return EnrichmentStatus(fact_id=fact_id, status=row[0])

    # ------------------------------------------------------------------
    # Ledger continuity
    # ------------------------------------------------------------------

    async def verify_ledger_continuity(self) -> LedgerContinuityResult:
        """Verify the cryptographic chain of the entire ledger.

        Delegates to engine.verify_ledger() which invokes LedgerVerifier.verify_chain().
        Returns a typed result instead of a raw dict.
        """
        try:
            raw: dict = await self.engine.verify_ledger()
            return LedgerContinuityResult(
                valid=raw.get("valid", False),
                checked_events=raw.get("checked_events", 0),
                violations=raw.get("violations", []),
            )
        except Exception as exc:
            logger.error("🔴 [ORACLE] Ledger audit failed: %s", exc)
            return LedgerContinuityResult(
                valid=False,
                checked_events=0,
                violations=[f"AUDIT_EXCEPTION: {exc}"],
            )
