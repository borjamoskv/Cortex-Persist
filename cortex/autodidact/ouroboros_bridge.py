# CORTEX Autodidact — Ouroboros Bridge (AX-044/045)
# Apache-2.0 · (c) 2026 CORTEX Swarm

"""Agentic feedback loop: Capital finances mathematics,
mathematics validates the ledger.

AX-044: A CAPITAL transaction can allocate exergy to fund
a proof-search (KNOWLEDGE quest).

AX-045: A completed KNOWLEDGE proof retroactively validates
the capital chain that funded it, closing the Ouroboros.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.autodidact.dual_ledger import DualLedger, TxType

__all__ = ["OuroborosBridge"]

logger = logging.getLogger("cortex.autodidact.ouroboros_bridge")


class OuroborosBridge:
    """Bidirectional Capital ↔ Knowledge entanglement (AX-044/045).

    The bridge records cross-references between streams so any
    audit can trace which capital funded which proof and which
    proof validated which capital extraction.

    Parameters
    ----------
    ledger : DualLedger
        The unified dual-stream hash-chain.
    """

    def __init__(self, ledger: DualLedger) -> None:
        self.ledger = ledger

    # ── AX-044: Capital → Knowledge ─────────────────────────────

    async def fund_proof_search(
        self,
        capital_tx_hash: str,
        target_problem: str,
        allocated_exergy_usd: float = 0.0,
        *,
        metadata: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> str:
        """Link a CAPITAL tx to a KNOWLEDGE allocation.

        Records a KNOWLEDGE entry that references the capital source,
        creating a cryptographic funding trail.

        Returns the knowledge_tx_hash.
        """
        detail: dict[str, Any] = {
            "funding_source": capital_tx_hash,
            "target_problem": target_problem,
            "allocated_exergy_usd": allocated_exergy_usd,
            **(metadata or {}),
        }

        tx_hash = await self.ledger.record_knowledge(
            project="millennium",
            action="proof_search_funded",
            detail=detail,
            tenant_id=tenant_id,
            skip_cache=True,  # Funding is always unique
        )

        logger.info(
            "AX-044: Capital %s → Knowledge %s (problem=%s, $%.2f)",
            capital_tx_hash[:12], tx_hash[:12], target_problem, allocated_exergy_usd,
        )
        return tx_hash

    # ── AX-045: Knowledge → Capital ─────────────────────────────

    async def validate_capital_via_proof(
        self,
        knowledge_tx_hash: str,
        validated_capital_hashes: list[str],
        proof_summary: str = "",
        *,
        tenant_id: str = "default",
    ) -> str:
        """A completed proof retroactively validates capital entries.

        Records a KNOWLEDGE tx that certifies the referenced CAPITAL
        transactions, closing the Ouroboros loop.

        Returns the validation_tx_hash.
        """
        detail: dict[str, Any] = {
            "proof_source": knowledge_tx_hash,
            "validated_capital": validated_capital_hashes,
            "proof_summary": proof_summary,
        }

        tx_hash = await self.ledger.record_knowledge(
            project="millennium",
            action="capital_validated",
            detail=detail,
            tenant_id=tenant_id,
            skip_cache=True,
        )

        logger.info(
            "AX-045: Proof %s validates %d capital entries → %s",
            knowledge_tx_hash[:12], len(validated_capital_hashes), tx_hash[:12],
        )
        return tx_hash

    # ── Convenience ──────────────────────────────────────────────

    async def close_loop(
        self,
        capital_tx_hash: str,
        target_problem: str,
        proof_summary: str,
        allocated_exergy_usd: float = 0.0,
        *,
        tenant_id: str = "default",
    ) -> dict[str, str]:
        """Full Ouroboros cycle: fund → prove → validate.

        Returns dict with ``funding_hash`` and ``validation_hash``.
        """
        funding_hash = await self.fund_proof_search(
            capital_tx_hash=capital_tx_hash,
            target_problem=target_problem,
            allocated_exergy_usd=allocated_exergy_usd,
            tenant_id=tenant_id,
        )

        validation_hash = await self.validate_capital_via_proof(
            knowledge_tx_hash=funding_hash,
            validated_capital_hashes=[capital_tx_hash],
            proof_summary=proof_summary,
            tenant_id=tenant_id,
        )

        return {"funding_hash": funding_hash, "validation_hash": validation_hash}
