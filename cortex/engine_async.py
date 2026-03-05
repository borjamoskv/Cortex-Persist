import asyncio
import logging
import random
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.cuatrida.models import Dimension
from cortex.database.pool import CortexConnectionPool
from cortex.database.writer import SqliteWriteWorker
from cortex.embeddings import LocalEmbedder
from cortex.engine.agent_mixin import AgentMixin
from cortex.engine.consensus import ConsensusMixin
from cortex.engine.history import HistoryMixin
from cortex.engine.ledger import ImmutableLedger
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.search_mixin import SearchMixin

# Mixins
from cortex.engine.store_mixin import StoreMixin
from cortex.graph import get_graph as _get_graph
from cortex.memory.temporal import now_iso
from cortex.utils.canonical import canonical_json, compute_tx_hash
from cortex.utils.result import Err, Ok, Result

__all__ = ["TX_BEGIN_IMMEDIATE", "AsyncCortexEngine"]

logger = logging.getLogger("cortex.engine.async")

TX_BEGIN_IMMEDIATE = "BEGIN IMMEDIATE"


class AsyncCortexEngine(
    StoreMixin, QueryMixin, SearchMixin, AgentMixin, ConsensusMixin, HistoryMixin
):
    """
    Native async database engine for CORTEX.
    Protocol: MEJORAlo God Mode 8.0 - Wave 3 Structural Correction
    """

    def __init__(
        self,
        pool: CortexConnectionPool,
        db_path: str,
        writer: SqliteWriteWorker | None = None,
    ):
        self._pool = pool
        self._db_path = Path(db_path)
        self._writer = writer
        self._embedder: LocalEmbedder | None = None
        self._ledger: ImmutableLedger | None = None

        # Dimension A-D: The Cuátrida Entity
        from cortex.cuatrida.orchestrator import CuatridaOrchestrator

        self._cuatrida = CuatridaOrchestrator(self)

    @property
    def cuatrida(self) -> Any:
        """Access the Cuátrida Orchestrator (Dimensions A-D)."""
        return self._cuatrida

    @property
    def writer(self) -> SqliteWriteWorker | None:
        """Access the sovereign write worker (Single Writer Queue)."""
        return self._writer

    async def write(self, sql: str, params: tuple[Any, ...] = ()) -> Result[int, str]:
        """Execute a write via the sovereign writer if available, else via pool.

        Returns Result[int, str] — Ok(rowcount) or Err(message).
        """
        if self._writer and self._writer.is_running:
            return await self._writer.execute(sql, params)
        
        # Protocolo TRAMPOLIN: Triangulación antifrágil con Jitter (Axioma Ω6)
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                async with self.session() as conn:
                    cursor = await conn.execute(sql, params)
                    await conn.commit()
                    # Return lastrowid for inserts to support tx_id tracking
                    if sql.strip().upper().startswith("INSERT"):
                        return Ok(cursor.lastrowid)  # type: ignore[reportReturnType]
                    return Ok(cursor.rowcount)
            except (sqlite3.Error, OSError) as e:
                if "database is locked" not in str(e).lower() or attempt >= max_retries:
                    return Err(f"Pool write error: {e}")
                
                # Jitter asimétrico: backoff de 0.5s, 1.5s, 4.5s + entropía
                sleep_time = (0.5 * (3 ** attempt)) + random.uniform(0.1, 0.5)
                logger.warning(
                    "TRAMPOLIN: WAL Locked en write(). Exhalando %.2fs (intento %d/%d)...",
                    sleep_time, attempt + 1, max_retries
                )
                await asyncio.sleep(sleep_time)
                
        return Err("Pool write error: Exceeded max retries for DB Lock.")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Proporciona una sesión transaccional (conexión) desde el pool."""
        async with self._pool.acquire() as conn:
            yield conn

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    async def get_conn(self) -> aiosqlite.Connection:
        """Alias for compatibility with standard CORTEX mixins."""
        return await self._pool.acquire().__aenter__()

    def _get_ledger(self) -> ImmutableLedger:
        if self._ledger is None:
            self._ledger = ImmutableLedger(self._pool)
        return self._ledger

    async def _log_transaction(
        self, conn: aiosqlite.Connection, project: str, action: str, detail: dict[str, Any]
    ) -> int:
        dj = canonical_json(detail)
        ts = now_iso()
        async with conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1") as cursor:
            prev = await cursor.fetchone()
            ph = prev[0] if prev else "GENESIS"

        th = compute_tx_hash(ph, project, action, dj, ts)

        cursor = await conn.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, COALESCE((SELECT hash FROM transactions ORDER BY id DESC LIMIT 1), "
            "'GENESIS'), ?, ?)",
            (project, action, dj, th, ts),
        )
        # Re-calc hash with actual ph from the DB to be absolute
        async with conn.execute(
            "SELECT prev_hash FROM transactions WHERE id = ?", (cursor.lastrowid,)
        ) as c2:
            row = await c2.fetchone()
            actual_ph = row[0] if row else ph
            if actual_ph != ph:
                # Re-hash if it changed under our feet
                th = compute_tx_hash(actual_ph, project, action, dj, ts)
                await conn.execute(
                    "UPDATE transactions SET hash = ? WHERE id = ?", (th, cursor.lastrowid)
                )

        tx_id = cursor.lastrowid
        self._get_ledger().record_write()

        # Cuátrida Hook: Dimension B (Temporal Sovereignty)
        if self._cuatrida:
            await self._cuatrida.log_decision(
                project=project,
                intent=action,
                dimension=Dimension.TEMPORAL_SOVEREIGNTY,
                metadata={"tx_id": tx_id, "detail": detail},
                conn=conn,
            )

        return tx_id  # type: ignore[reportReturnType]

    # store() and deprecate() are now provided by StoreMixin
    # register_agent(), get_agent(), list_agents() are now provided by AgentMixin
    # search() is now provided by SearchMixin
    # All core fact operations (recall, search, retrieve, stats) are now provided by mixins

    async def verify_ledger(self) -> dict[str, Any]:
        return await self._get_ledger().verify_integrity_async()

    async def create_checkpoint(self) -> int | None:
        return await self._get_ledger().create_checkpoint_async()

    async def verify_vote_ledger(self) -> dict[str, Any]:
        return await super().verify_vote_ledger()

    async def get_graph(self, project: str | None = None, limit: int = 50) -> dict[str, Any]:
        async with self.session() as conn:
            return await _get_graph(conn, project, limit)

    async def health_check(self) -> bool:
        try:
            async with self.session() as conn:
                async with conn.execute("SELECT 1") as cursor:
                    await cursor.fetchone()
            return True
        except (sqlite3.Error, OSError, ValueError):
            return False
