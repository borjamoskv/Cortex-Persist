# CORTEX Autodidact — Dual Ledger (AX-041)
# Apache-2.0 · (c) 2026 CORTEX Swarm

"""Unified hash-chain with dual-stream transaction types.

Capital (Ouroboros) and Knowledge (Millennium) entries share
a single prev_hash linkage so every MEV extraction is
cryptographically entangled with the math proof that validated it.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from cortex.autodidact.kv_cache import KVPrefixCache
from cortex.ledger.sovereign_ledger import SovereignLedger
from cortex.utils.canonical import canonical_json

__all__ = ["DualLedger", "TxType"]

logger = logging.getLogger("cortex.autodidact.dual_ledger")


class TxType(Enum):
    """Transaction stream discriminator."""

    CAPITAL = "capital"      # MEV, bounties, arbitrage, funding
    KNOWLEDGE = "knowledge"  # Proofs, theorems, PeARL programs, concepts


class DualLedger:
    """Single hash-chain, dual-stream sovereign ledger (AX-041).

    Wraps ``SovereignLedger`` and injects ``tx_type`` into every
    transaction detail so the chain can be sliced by stream while
    maintaining a single sequential prev_hash linkage.

    Parameters
    ----------
    sovereign : SovereignLedger
        Underlying hash-chain implementation (SQLite + Merkle).
    kv_cache : KVPrefixCache
        Prefix cache for identical-strike deduplication (AX-042).
    """

    def __init__(self, sovereign: SovereignLedger, kv_cache: KVPrefixCache | None = None) -> None:
        self.sovereign = sovereign
        self.kv_cache = kv_cache or KVPrefixCache()

    async def ensure_table(self) -> None:
        """Propagate table creation to the underlying ledger."""
        await self.sovereign.ensure_table()

    # ── Write Path ───────────────────────────────────────────────

    async def record(
        self,
        tx_type: TxType,
        project: str,
        action: str,
        detail: dict[str, Any],
        *,
        tenant_id: str = "default",
        skip_cache: bool = False,
    ) -> str:
        """Record a dual-stream transaction.

        The ``tx_type`` is injected into ``detail`` as ``_stream`` so
        audits can filter by stream without breaking the hash-chain.

        Returns the SHA-256 tx_hash.
        """
        # Inject stream discriminator
        enriched = {**detail, "_stream": tx_type.value}

        # KV-Aware dedup (AX-042)
        if not skip_cache:
            prefix_key = self.kv_cache.compute_prefix(tx_type.value, action, enriched)
            if self.kv_cache.hit(prefix_key):
                cached_hash = self.kv_cache.get(prefix_key)
                logger.debug("KV-HIT [%s/%s] → %s", tx_type.value, action, cached_hash[:12])
                return cached_hash

        tx_hash = await self.sovereign.record_transaction(
            project=project,
            action=action,
            detail=enriched,
            tenant_id=tenant_id,
        )

        # Populate cache
        if not skip_cache:
            self.kv_cache.store(prefix_key, tx_hash)  # type: ignore[possibly-undefined]

        logger.info(
            "DUAL-TX [%s] %s/%s → %s",
            tx_type.value, project, action, tx_hash[:16],
        )
        return tx_hash

    async def record_capital(
        self, project: str, action: str, detail: dict[str, Any], **kw: Any
    ) -> str:
        """Shortcut for CAPITAL transactions."""
        return await self.record(TxType.CAPITAL, project, action, detail, **kw)

    async def record_knowledge(
        self, project: str, action: str, detail: dict[str, Any], **kw: Any
    ) -> str:
        """Shortcut for KNOWLEDGE transactions."""
        return await self.record(TxType.KNOWLEDGE, project, action, detail, **kw)

    # ── Read / Audit Path ────────────────────────────────────────

    async def audit_integrity(self, tenant_id: str = "default") -> dict[str, Any]:
        """Full chain verification delegated to SovereignLedger."""
        return await self.sovereign.audit_integrity(tenant_id=tenant_id)

    async def audit_dual(self, tenant_id: str = "default") -> dict[str, Any]:
        """Extended audit: chain integrity + per-stream metrics.

        Returns
        -------
        dict with keys: valid, violations, tx_count,
        capital_count, knowledge_count, exergy_balance.
        """
        base = await self.sovereign.audit_integrity(tenant_id=tenant_id)

        # Stream-level accounting
        capital_count = 0
        knowledge_count = 0
        exergy_sum = 0.0

        async with self.sovereign._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT detail FROM transactions WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            )
            import json

            async for (detail_json,) in cursor:
                try:
                    d = json.loads(detail_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                stream = d.get("_stream")
                if stream == TxType.CAPITAL.value:
                    capital_count += 1
                    exergy_sum += float(d.get("exergy_usd", 0))
                elif stream == TxType.KNOWLEDGE.value:
                    knowledge_count += 1

        return {
            **base,
            "capital_count": capital_count,
            "knowledge_count": knowledge_count,
            "exergy_balance": exergy_sum,
            "cache_stats": self.kv_cache.stats(),
        }
