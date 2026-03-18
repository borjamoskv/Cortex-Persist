import asyncio
import logging
import random
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from cortex.database.pool import CortexConnectionPool
from cortex.database.writer import SqliteWriteWorker
from cortex.embeddings import LocalEmbedder
from cortex.engine.agent_mixin import AgentMixin
from cortex.engine.consensus import ConsensusMixin
from cortex.engine.history import HistoryMixin
from cortex.engine.ledger import ImmutableLedger
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.search_mixin import SearchMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.extensions.cuatrida.models import Dimension
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
    def __init__(
        self,
        pool: CortexConnectionPool,
        db_path: str,
        writer: Optional[SqliteWriteWorker] = None,
    ):
        self._pool = pool
        self._db_path = Path(db_path)
        self._writer = writer
        self._embedder: Optional[LocalEmbedder] = None
        self._ledger: Optional[ImmutableLedger] = None
        self.vault: Optional[Any] = None

        from cortex.extensions.cuatrida.orchestrator import CuatridaOrchestrator

        self._cuatrida = CuatridaOrchestrator(self)
        self._trust_registry: Optional[Any] = None

    @property
    def cuatrida(self) -> Any:
        return self._cuatrida

    def get_trust_registry(self) -> Any:
        """Access the Bayesian Trust Registry (Ω₃)."""
        if self._trust_registry is None:
            from cortex.engine.trust_registry import TrustRegistry

            self._trust_registry = TrustRegistry()
        return self._trust_registry

    async def propagate_taint(self, fact_id: int, tenant_id: str = "default") -> Any:
        """Propagate taint (Ω₁₃) through the causal DAG."""
        from cortex.engine.causality import AsyncCausalGraph

        async with self.session() as conn:
            graph = AsyncCausalGraph(conn)
            return await graph.propagate_taint(fact_id, tenant_id=tenant_id)

    @property
    def writer(self) -> Optional[SqliteWriteWorker]:
        return self._writer

    async def write(self, sql: str, params: tuple[Any, ...] = ()) -> Result[int, str]:
        if self._writer and self._writer.is_running:
            return await self._writer.execute(sql, params)
        return await self._attempt_write_with_retries(sql, params)

    async def _attempt_write_with_retries(
        self, sql: str, params: tuple[Any, ...]
    ) -> Result[int, str]:
        max_retries = 3
        for attempt in range(max_retries + 1):
            result = await self._try_execute_write(sql, params, attempt, max_retries)
            if result is not None:
                return result
        return Err("Pool write error: Exceeded max retries for DB Lock.")

    async def _try_execute_write(
        self, sql: str, params: tuple[Any, ...], attempt: int, max_retries: int
    ) -> Optional[Result[int, str]]:
        try:
            result = await self._execute_write(sql, params)
            if result:
                return result
        except (sqlite3.Error, OSError) as e:
            if "database is locked" not in str(e).lower() or attempt >= max_retries:
                return Err(f"Pool write error: {e}")
            await self._backoff(attempt)
        return None

    async def _execute_write(self, sql: str, params: tuple[Any, ...]) -> Optional[Result[int, str]]:
        async with self.session() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            if sql.strip().upper().startswith("INSERT"):
                return Ok(cursor.lastrowid)  # type: ignore[type-error]
            return Ok(cursor.rowcount)

    async def _backoff(self, attempt: int):
        sleep_time = (0.5 * (3**attempt)) + random.uniform(0.1, 0.5)
        logger.warning(
            "TRAMPOLIN: WAL Locked en write(). Exhalando %.2fs (intento %d/%d)...",
            sleep_time,
            attempt + 1,
            3,
        )
        await asyncio.sleep(sleep_time)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._pool.acquire() as conn:
            yield conn

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    async def get_conn(self) -> aiosqlite.Connection:
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
        prev_hash = await self._get_previous_hash(conn)
        th = compute_tx_hash(prev_hash, project, action, dj, ts)

        cursor = await conn.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, prev_hash, th, ts),
        )
        await self._update_transaction_hash_if_needed(
            conn,
            cursor.lastrowid,
            project,
            action,
            dj,
            ts,
            prev_hash,  # type: ignore[type-error]
        )
        tx_id = cursor.lastrowid
        self._get_ledger().record_write()

        if self._cuatrida:
            await self._cuatrida.log_decision(
                project=project,
                intent=action,
                dimension=Dimension.TEMPORAL_SOVEREIGNTY,
                metadata={"tx_id": tx_id, "detail": detail},
                conn=conn,
            )
        return tx_id  # type: ignore[type-error]

    async def _get_previous_hash(self, conn: aiosqlite.Connection) -> str:
        async with conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1") as cursor:
            prev = await cursor.fetchone()
            return prev[0] if prev else "GENESIS"

    async def _update_transaction_hash_if_needed(
        self,
        conn: aiosqlite.Connection,
        tx_id: int,
        project: str,
        action: str,
        dj: str,
        ts: str,
        initial_ph: str,
    ):
        async with conn.execute("SELECT prev_hash FROM transactions WHERE id = ?", (tx_id,)) as c2:
            row = await c2.fetchone()
            actual_ph = row[0] if row else initial_ph
            if actual_ph != initial_ph:
                th = compute_tx_hash(actual_ph, project, action, dj, ts)
                await conn.execute("UPDATE transactions SET hash = ? WHERE id = ?", (th, tx_id))

    async def verify_ledger(self) -> dict[str, Any]:
        return await self._get_ledger().verify_integrity_async()

    async def create_checkpoint(self) -> Optional[int]:
        return await self._get_ledger().create_checkpoint_async()

    async def verify_vote_ledger(self) -> dict[str, Any]:
        return await super().verify_vote_ledger()

    async def get_graph(self, project: Optional[str] = None, limit: int = 50) -> dict[str, Any]:
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
