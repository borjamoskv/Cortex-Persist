# [C5-REAL] Exergy-Maximized
"""
Sovereign Immutable Ledger (CHRONOS-1 Standard).

Axiom Reference:
- Ω₃ (Byzantine Default): "I verify, then trust. Never reversed."
- Ω₂ (Entropic Asymmetry): "Merkle Trees reduce trust-cost from O(N) to O(log N)."
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex.database.core import causal_write
from cortex.utils.canonical import (
    canonical_json,
    compute_tx_hash,
    now_iso,
)

logger = logging.getLogger("cortex.ledger")


from .merkle import MerkleTree
from .mixins.audit import LedgerAuditMixin


class SovereignLedger(LedgerAuditMixin):
    """The Custodian of Immutable History (CORTEX Wave 5/8).

    Unified implementation supporting both synchronous single-connection
    and asynchronous pool-based operations. Implements adaptive
    checkpointing and v2 canonical hashing.
    """

    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, db: sqlite3.Connection | aiosqlite.Connection | CortexConnectionPool):
        from cortex import config

        self.db = db
        self._write_timestamps: deque[float] = deque(maxlen=5000)
        self._config = config

        # Schema is created synchronously on init if possible
        if self._is_sync_connection(db):
            self._ensure_schema_sync(cast(sqlite3.Connection, db))

    @property
    def _lock(self) -> asyncio.Lock:
        from cortex.utils.locks import get_loop_lock

        return get_loop_lock(self, "ledger")

    @staticmethod
    def _is_sync_connection(db: object) -> bool:
        """Return true for sqlite-compatible synchronous connections.

        Some test/runtime wrappers expose the sqlite3 connection protocol
        without preserving a strict ``sqlite3.Connection`` identity.
        """
        if isinstance(db, aiosqlite.Connection):
            return False
        return isinstance(db, sqlite3.Connection) or all(
            hasattr(db, attr) for attr in ("execute", "commit", "rollback")
        )

    def _sync_db(self) -> sqlite3.Connection:
        if not self._is_sync_connection(self.db):
            raise RuntimeError("operation requires a sync sqlite3.Connection")
        return cast(sqlite3.Connection, self.db)

    def _ensure_schema_sync(self, conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       TEXT NOT NULL DEFAULT '__global__',
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type      TEXT NOT NULL,
                status          TEXT NOT NULL,
                details         TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_prev ON transactions(prev_hash);
            CREATE INDEX IF NOT EXISTS idx_merkle_range ON merkle_roots(tx_start_id, tx_end_id);
        """)
        self._ensure_ledger_column(
            conn,
            "transactions",
            "tenant_id",
            "TEXT NOT NULL DEFAULT 'default'",
        )
        self._ensure_ledger_column(
            conn,
            "merkle_roots",
            "tenant_id",
            "TEXT NOT NULL DEFAULT '__global__'",
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_tenant_id ON transactions(tenant_id, id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_merkle_tenant_range "
            "ON merkle_roots(tenant_id, tx_start_id, tx_end_id)"
        )

    @staticmethod
    def _ensure_ledger_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def record_write(self) -> None:
        """Track write rate for adaptive checkpointing."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW if self._write_timestamps else 0
        if rate > self.HIGH_WRITE_THRESHOLD:
            return getattr(self._config, "CHECKPOINT_MIN", 10)
        return getattr(self._config, "CHECKPOINT_MAX", 100)

    @staticmethod
    def _effective_tenant_id(tenant_id: str | None) -> str:
        return tenant_id or "default"

    def record_transaction(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction synchronously."""
        conn = self._sync_db()

        self.record_write()
        detail_json = canonical_json(detail) if detail else "{}"
        ts = now_iso()
        effective_tenant_id = self._effective_tenant_id(tenant_id)

        try:
            conn.execute("BEGIN EXCLUSIVE")
            new_hash = self._record_transaction_sync_unlocked(
                conn,
                project,
                action,
                detail_json,
                ts,
                effective_tenant_id,
            )
            conn.commit()
            return new_hash
        except sqlite3.Error:
            conn.rollback()
            raise

    def record_transaction_in_current_transaction(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction inside the caller's active SQLite transaction."""
        conn = self._sync_db()

        self.record_write()
        return self._record_transaction_sync_unlocked(
            conn,
            project,
            action,
            canonical_json(detail) if detail else "{}",
            now_iso(),
            self._effective_tenant_id(tenant_id),
        )

    def _record_transaction_sync_unlocked(
        self,
        conn: sqlite3.Connection,
        project: str,
        action: str,
        detail_json: str,
        timestamp: str,
        tenant_id: str,
    ) -> str:
        # [OUROBOROS] C5-REAL Entropy Control & Autopoiesis Hook
        if not action or action.isspace():
            raise ValueError("[OUROBOROS] Vector P1.2: Anergic action detected. Ledger requires high exergy.")
        if len(detail_json) < 2:
            logger.warning("[OUROBOROS] Low entropy transaction detail. Sub-optimal exergy flow.")
            
        # [C5-REAL] Context Isolation Hook (P1.2)
        if "slop" in action.lower() or "limerence" in action.lower():
            raise ValueError("[OUROBOROS] Vector P1.2 Context Isolation: Action blocked by C5-REAL Anti-Limerence protocol.")

        cursor = conn.execute(
            "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = cursor.fetchone()
        prev_hash = row[0] if row else "GENESIS"
        new_hash = compute_tx_hash(prev_hash, project, action, detail_json, timestamp, tenant_id)
        with causal_write(conn):
            conn.execute(
                "INSERT INTO transactions "
                "(project, action, detail, prev_hash, hash, tenant_id, timestamp)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (project, action, detail_json, prev_hash, new_hash, tenant_id, timestamp),
            )
        return new_hash

    async def record_transaction_async(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction asynchronously (requires a connection pool)."""
        self.record_write()
        detail_json = canonical_json(detail) if detail else "{}"
        ts = now_iso()
        effective_tenant_id = self._effective_tenant_id(tenant_id)

        async with self._get_conn_proxy() as conn:  # type: ignore[reportAttributeAccessIssue]
            await conn.execute("BEGIN EXCLUSIVE")
            try:
                cursor = await conn.execute(
                    "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                    (effective_tenant_id,),
                )
                row = await cursor.fetchone()
                prev_hash = row[0] if row else "GENESIS"
                new_hash = compute_tx_hash(
                    prev_hash,
                    project,
                    action,
                    detail_json,
                    ts,
                    effective_tenant_id,
                )

                await conn.execute(
                    "INSERT INTO transactions "
                    "(project, action, detail, prev_hash, hash, tenant_id, timestamp)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (project, action, detail_json, prev_hash, new_hash, effective_tenant_id, ts),
                )
                await conn.commit()
                return new_hash
            except (aiosqlite.Error, sqlite3.Error, TypeError, ValueError):
                await conn.rollback()
                raise

    def create_checkpoint(self) -> str | None:
        """Create a Merkle checkpoint synchronously."""
        if not self._is_sync_connection(self.db):
            return None
        conn = self._sync_db()

        batch_size = self.adaptive_batch_size
        cursor = conn.execute(
            "SELECT MAX(tx_end_id) FROM merkle_roots WHERE tenant_id = '__global__'"
        )
        row = cursor.fetchone()
        last_covered = row[0] or 0 if row else 0

        cursor = conn.execute(
            "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id LIMIT ?",
            (last_covered, batch_size),
        )
        rows = cursor.fetchall()

        if not rows or len(rows) < batch_size:
            return None

        hashes = [r[1] for r in rows]
        tree = MerkleTree(hashes)
        root = tree.root_hash
        start_id, end_id = rows[0][0], rows[-1][0]

        conn.execute(
            "INSERT INTO merkle_roots "
            "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
            "VALUES ('__global__', ?, ?, ?, ?)",
            (root, start_id, end_id, len(rows)),
        )
        conn.commit()
        return root

    async def create_checkpoint_async(self, conn: aiosqlite.Connection | None = None) -> str | None:
        """Create a Merkle checkpoint asynchronously."""
        async with self._lock:
            if conn is not None:
                return await self._create_checkpoint_async_impl(conn, commit=False)
            async with self._get_conn_proxy() as proxy_conn:
                return await self._create_checkpoint_async_impl(proxy_conn, commit=True)

    async def _create_checkpoint_async_impl(
        self, conn: aiosqlite.Connection, commit: bool = True
    ) -> str | None:
        batch_size = self.adaptive_batch_size
        cursor = await conn.execute(
            "SELECT MAX(tx_end_id) FROM merkle_roots WHERE tenant_id = '__global__'"
        )
        row = await cursor.fetchone()
        last_covered = row[0] or 0 if row else 0

        cursor = await conn.execute(
            "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id LIMIT ?",
            (last_covered, batch_size),
        )
        rows = list(await cursor.fetchall())

        if not rows or len(rows) < batch_size:
            return None

        hashes = [r[1] for r in rows]
        tree = MerkleTree(hashes)
        root = tree.root_hash
        start_id, end_id = rows[0][0], rows[-1][0]

        await conn.execute(
            "INSERT INTO merkle_roots "
            "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
            "VALUES ('__global__', ?, ?, ?, ?)",
            (root, start_id, end_id, len(rows)),
        )
        if commit:
            await conn.commit()
        return root

    @asynccontextmanager
    async def _get_conn_proxy(self) -> AsyncIterator[aiosqlite.Connection]:
        """Internal helper to get a connection for auditing/writing,
        supporting both Pool and raw Connection (Ω₁).
        """
        if isinstance(self.db, aiosqlite.Connection):
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            conn_loop = getattr(self.db, "_cortex_loop", None)
            if conn_loop is None or current_loop is None or conn_loop is current_loop:
                yield self.db
                return

            db_path = getattr(self.db, "_cortex_db_path", None)
            if not db_path:
                try:
                    db_path = self.db._connector.__closure__[0].cell_contents  # type: ignore
                except (AttributeError, IndexError, TypeError):
                    db_path = None

            if db_path:
                from cortex.database.core import connect_async

                conn = await connect_async(str(db_path))
                try:
                    yield conn
                finally:
                    await conn.close()
                return

            yield self.db
            return

        if self._is_sync_connection(self.db):
            raise RuntimeError("Async ledger operations require a CortexConnectionPool backend")

        pool = cast("CortexConnectionPool", self.db)
        async with pool.acquire() as conn:
            yield conn
