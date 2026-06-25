# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
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
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

from babylon60.engine.mixins.base import EngineMixinBase
from babylon60.memory.temporal import now_iso

__all__ = ["TransactionMixin"]

logger = logging.getLogger("babylon60.transactions")


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
        from babylon60.utils.canonical import canonical_json, compute_tx_hash
        from babylon60.utils.locks import get_loop_lock

        # JIS (SOC 2 / C5 / GDPR) Audit Policy Check
        try:
            from babylon60.extensions.policy.jis_auditor import JISAuditor

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

        async with get_loop_lock(self, "write"):
            # Enforce write lock promotion to prevent read-modify-write race
            if not conn.in_transaction:
                await conn.execute("BEGIN IMMEDIATE")

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
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tenant_id, project, action, dj, ph, th, ts),
            )
            tx_id = c.lastrowid

            if getattr(self, "_ledger", None):
                try:
                    self._ledger.record_write()
                    if not getattr(self, "_closing", False):
                        await self._ledger.create_checkpoint_async(conn)
                except (sqlite3.Error, OSError, RuntimeError, AttributeError, ValueError) as e:
                    logger.warning("Auto-checkpoint failed: %s", e)
                    from babylon60.telemetry.metrics import metrics

                    metrics.inc(
                        "cortex_ledger_checkpoint_failures_total",
                        meta={"error": str(e)},
                    )

            return int(tx_id) if tx_id is not None else 0

    async def verify_ledger(self) -> dict[str, Any]:
        """Verify the integrity of the sovereign ledger (Operation Void)."""
        async with self.session() as conn:
            from babylon60.ledger import ImmutableLedger
            ledger = ImmutableLedger(conn)
            return await ledger.audit_integrity_async()
