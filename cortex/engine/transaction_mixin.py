"""Transaction mixin — log, verify, and process ledger events."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.temporal import now_iso

logger = logging.getLogger("cortex.transactions")


class TransactionMixin:
    """Sovereign Ledger Transaction and CDC (Change Data Capture) management."""

    async def _log_transaction(
        self, conn: aiosqlite.Connection, project: str, action: str, detail: dict[str, Any]
    ) -> int:
        from cortex.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = await conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        prev = await cursor.fetchone()
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
                from cortex.metrics import metrics

                metrics.inc(
                    "cortex_ledger_checkpoint_failures_total",
                    meta={"error": str(e)},
                )

        return tx_id

    async def verify_ledger(self) -> dict[str, Any]:
        if not getattr(self, "_ledger", None):
            from cortex.engine.ledger import ImmutableLedger

            self._ledger = ImmutableLedger(await self.get_conn())
        return await self._ledger.verify_integrity_async()

    async def process_graph_outbox_async(self, limit: int = 10) -> int:
        from cortex.graph.backends.neo4j import Neo4jBackend

        conn = await self.get_conn()
        async with conn.execute(
            "SELECT id, fact_id, action FROM graph_outbox WHERE status = 'pending' LIMIT ?",
            (limit,),
        ) as cursor:
            events = await cursor.fetchall()

        if not events:
            return 0

        processed_count = 0
        try:
            neo4j = Neo4jBackend()
            if not neo4j._initialized:
                return 0
        except ImportError:
            return 0

        for event_id, fact_id, action in events:
            try:
                success = False
                if action == "deprecate_fact":
                    success = await neo4j.delete_fact_elements(fact_id)

                status = "processed" if success else "failed"
                await conn.execute(
                    "UPDATE graph_outbox SET status = ?, processed_at = ?, "
                    "retry_count = retry_count + 1 WHERE id = ?",
                    (status, now_iso(), event_id),
                )
                processed_count += 1
            except (sqlite3.Error, OSError, RuntimeError, AttributeError) as e:
                logger.error("Failed to process CDC event %d: %s", event_id, e)
                await conn.execute(
                    "UPDATE graph_outbox SET status = 'failed', "
                    "retry_count = retry_count + 1 WHERE id = ?",
                    (event_id,),
                )

        await conn.commit()
        return processed_count
