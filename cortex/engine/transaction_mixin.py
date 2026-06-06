# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3
from typing import Any, cast

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase
from cortex.memory.temporal import now_iso

__all__ = ["TransactionMixin"]

logger = logging.getLogger("cortex.transactions")


class TransactionMixin(EngineMixinBase):
    """Sovereign Ledger - Immutable Transaction Log with Cryptographic Hash Chain.

    Every write operation produces a transaction record chained to its predecessor
    via ``compute_tx_hash(prev_hash, project, action, detail, timestamp)``.
    The chain is verified by ``ImmutableLedger.audit_integrity_async()``.

    CDC Pattern: ``_log_transaction()`` is the single write-path for all
    state mutations (store, deprecate, quarantine, unquarantine).
    """

    async def _log_transaction(
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        detail: dict[str, Any],
        tenant_id: str = "default",
    ) -> int:
        from cortex.utils.canonical import canonical_json, compute_tx_hash

        # JIS (SOC 2 / C5 / GDPR) Audit Policy Check
        try:
            from cortex.extensions.policy.jis_auditor import JISAuditor

            auditor = JISAuditor(enforce_encryption=False)  # Enforced softly
            violations = auditor.audit_payload(detail, event_id=f"tx_pending_{project}_{action}")
            if violations:
                logger.error(
                    f"JIS Policy violation in project '{project}' for action '{action}': {violations}"
                )
                # Depending on strictness, we might raise an Exception here,
                # but for now we log it as an error to track entropy.
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = await conn.execute(
            "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        prev = await cursor.fetchone()
        await cursor.close()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts, tenant_id=tenant_id)

        c = await conn.execute(
            "INSERT INTO transactions "
            "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, COALESCE((SELECT hash FROM transactions "
            "WHERE tenant_id = ? ORDER BY id DESC LIMIT 1), 'GENESIS'), ?, ?)",
            (tenant_id, project, action, dj, tenant_id, th, ts),
        )
        tx_id = c.lastrowid

        # Re-verify and update hash if prev_hash was different from our lookup
        async with conn.execute("SELECT prev_hash FROM transactions WHERE id = ?", (tx_id,)) as cur:
            row = await cur.fetchone()
            actual_ph = row[0] if row else ph
            if actual_ph != ph:
                th = compute_tx_hash(actual_ph, project, action, dj, ts, tenant_id=tenant_id)
                await conn.execute("UPDATE transactions SET hash = ? WHERE id = ?", (th, tx_id))

        if getattr(self, "_ledger", None):
            try:
                self._ledger.record_write()
                if not getattr(self, "_closing", False):
                    await self._ledger.create_checkpoint_async(conn)
            except (sqlite3.Error, OSError, RuntimeError, AttributeError, ValueError) as e:
                logger.warning("Auto-checkpoint failed: %s", e)
                from cortex.telemetry.metrics import metrics

                metrics.inc(
                    "cortex_ledger_checkpoint_failures_total",
                    meta={"error": str(e)},
                )

        return int(tx_id) if tx_id is not None else 0

    async def verify_ledger(self) -> dict[str, Any]:
        """Verify the integrity of the sovereign ledger (Operation Void)."""
        if not getattr(self, "_ledger", None):
            from cortex.ledger import ImmutableLedger

            # Pass the pool directly instead of a raw connection
            self._ledger = ImmutableLedger(cast(Any, self).pool)
        return await self._ledger.audit_integrity_async()
