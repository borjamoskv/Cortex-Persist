"""Transaction mixin — log, verify, and process ledger events."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase
from cortex.memory.temporal import now_iso

__all__ = ["TransactionMixin"]

logger = logging.getLogger("cortex.transactions")


class TransactionMixin(EngineMixinBase):
    """Sovereign Ledger — Immutable Transaction Log with Cryptographic Hash Chain.

    Every write operation produces a transaction record chained to its predecessor
    via ``compute_tx_hash(prev_hash, project, action, detail, timestamp)``.
    The chain is verified by ``ImmutableLedger.verify_integrity_async()``.

    CDC Pattern: ``_log_transaction()`` is the single write-path for all
    state mutations (store, deprecate, quarantine, unquarantine).
    """

    async def _log_transaction(
        self, conn: aiosqlite.Connection, project: str, action: str, detail: dict[str, Any]
    ) -> int:
        from cortex.utils.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = await conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        prev = await cursor.fetchone()
        await cursor.close()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts)

        c = await conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, COALESCE((SELECT hash FROM transactions "
            "ORDER BY id DESC LIMIT 1), 'GENESIS'), ?, ?)",
            (project, action, dj, th, ts),
        )
        tx_id = c.lastrowid

        # Re-verify and update hash if prev_hash was different from our lookup
        async with conn.execute("SELECT prev_hash FROM transactions WHERE id = ?", (tx_id,)) as cur:
            row = await cur.fetchone()
            actual_ph = row[0] if row else ph
            if actual_ph != ph:
                th = compute_tx_hash(actual_ph, project, action, dj, ts)
                await conn.execute("UPDATE transactions SET hash = ? WHERE id = ?", (th, tx_id))

        if getattr(self, "_ledger", None):
            try:
                self._ledger.record_write()
                await self._ledger.create_checkpoint_async()
            except (sqlite3.Error, OSError, RuntimeError, AttributeError) as e:
                logger.warning("Auto-checkpoint failed: %s", e)
                from cortex.telemetry.metrics import metrics

                metrics.inc(
                    "cortex_ledger_checkpoint_failures_total",
                    meta={"error": str(e)},
                )

        return int(tx_id) if tx_id is not None else 0

    async def verify_ledger(self) -> dict[str, Any]:
        if not getattr(self, "_ledger", None):
            from cortex.engine.ledger import ImmutableLedger

            conn = await self.get_conn()
            self._ledger = ImmutableLedger(conn)
        return await self._ledger.verify_integrity_async()
