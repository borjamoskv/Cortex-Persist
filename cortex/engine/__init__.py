"""CORTEX Engine — Package init."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import sqlite_vec

from cortex.config import DEFAULT_DB_PATH
from cortex.database.schema import get_init_meta
from cortex.embeddings import LocalEmbedder
from cortex.engine.memory_mixin import MemoryMixin
from cortex.engine.models import Fact, row_to_fact
from cortex.engine.query_mixin import _FACT_COLUMNS, _FACT_JOIN
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.transaction_mixin import TransactionMixin
from cortex.migrations.core import run_migrations_async
from cortex.telemetry.metrics import metrics

logger = logging.getLogger("cortex")


from cortex.consensus.manager import ConsensusManager  # noqa: E402
from cortex.embeddings.manager import EmbeddingManager  # noqa: E402
from cortex.facts.manager import FactManager  # noqa: E402


class CortexEngine(StoreMixin, MemoryMixin, TransactionMixin):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._conn: aiosqlite.Connection | None = None
        self._vec_available = False
        self._conn_lock = asyncio.Lock()
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)
        self._embedder: LocalEmbedder | None = None
        self._memory_manager = None  # Frontera 2: Tripartite Memory (lazy init)

        # Composition layers
        self.facts = FactManager(self)
        self.embeddings = EmbeddingManager(self)
        self.consensus = ConsensusManager(self)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        """Proporciona una sesión transaccional (conexión) válida."""
        conn = await self.get_conn()
        yield conn

    def _get_embedder(self) -> LocalEmbedder:
        """Protocol requirement for SearchMixin."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Connection ───────────────────────────────────────────────

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns the async database connection."""
        async with self._conn_lock:
            if self._conn is not None:
                return self._conn

            from cortex.database.core import connect_async

            self._conn = await connect_async(str(self._db_path))

            try:
                await self._conn.enable_load_extension(True)
                await self._conn.load_extension(sqlite_vec.loadable_path())
                await self._conn.enable_load_extension(False)
                self._vec_available = True
            except (OSError, AttributeError) as e:
                logger.debug("sqlite-vec extension not available: %s", e)
                self._vec_available = False

            return self._conn

    def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Connection not initialized. Call get_conn() first.")
        return self._conn

    def get_connection(self) -> aiosqlite.Connection:
        return self.get_conn()

    # ─── Backward Compatibility Aliases & Delegation ──────────────

    async def store(self, *args, **kwargs):
        return await self.facts.store(*args, **kwargs)

    async def store_many(self, *args, **kwargs):
        return await self.facts.store_many(*args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self.facts.search(*args, **kwargs)

    async def recall(self, *args, **kwargs):
        return await self.facts.recall(*args, **kwargs)

    async def update(self, *args, **kwargs):
        return await self.facts.update(*args, **kwargs)

    async def deprecate(self, *args, **kwargs):
        return await self.facts.deprecate(*args, **kwargs)

    async def history(self, *args, **kwargs):
        return await self.facts.history(*args, **kwargs)

    async def time_travel(self, *args, **kwargs):
        return await self.facts.time_travel(*args, **kwargs)

    async def reconstruct_state(self, *args, **kwargs):
        return await self.facts.reconstruct_state(*args, **kwargs)

    async def retrieve(self, fact_id: int):
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        from cortex.utils.errors import FactNotFound

        conn = await self.get_conn()
        cursor = await conn.execute(
            f"SELECT {_FACT_COLUMNS} {_FACT_JOIN} WHERE f.id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        fact = row_to_fact(row) if row else None
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def get_context_subgraph(self, *args, **kwargs):
        return await self.facts.get_context_subgraph(*args, **kwargs)

    async def find_path(self, *args, **kwargs):
        return await self.facts.find_path(*args, **kwargs)

    async def vote(self, *args, **kwargs):
        return await self.consensus.vote(*args, **kwargs)

    async def stats(self):
        return await self.facts.stats()

    # ─── Schema ───────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        from cortex.database.schema import get_all_schema
        from cortex.engine.ledger import ImmutableLedger

        conn = await self.get_conn()

        for stmt in get_all_schema():
            if "USING vec0" in stmt and not self._vec_available:
                continue
            await conn.executescript(stmt)
        await conn.commit()

        await run_migrations_async(conn)

        for k, v in get_init_meta():
            await conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        await conn.commit()

        self._ledger = ImmutableLedger(conn)
        await self._init_memory_subsystem(self._db_path, conn)
        metrics.set_engine(self)
        logger.info("CORTEX database initialized (async) at %s", self._db_path)

    # ─── Helpers ──────────────────────────────────────────────────

    def export_snapshot(self, out_path: str | Path) -> str:
        # Note: export_snapshot itself might be sync/blocking, consider if it needs move or refactor
        from cortex.sync.snapshot import export_snapshot

        return export_snapshot(self, out_path)

    @staticmethod
    def _row_to_fact(row) -> Fact:
        return row_to_fact(row)

    # ─── Lifecycle ────────────────────────────────────────────────

    async def close(self):
        if self._memory_manager:
            await self._memory_manager.wait_for_background()
            self._memory_manager = None
        if self._conn:
            await self._conn.close()
            self._conn = None
        self._ledger = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
