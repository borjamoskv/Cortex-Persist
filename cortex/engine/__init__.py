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
        self._enforce_fs_permissions()
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

    # ─── Security: Filesystem Permission Enforcement ──────────────

    def _enforce_fs_permissions(self) -> None:
        """Enforce restrictive permissions on CORTEX data directory and DB file.
        Directory: 700 (owner-only rwx). DB file: 600 (owner-only rw).
        """
        import os

        parent = self._db_path.parent
        try:
            # Directory: rwx------ (700)
            current_dir_mode = parent.stat().st_mode & 0o777
            if current_dir_mode != 0o700:
                os.chmod(parent, 0o700)
                logger.info(
                    "SECURITY: Fixed dir perms %o → 700 on %s",
                    current_dir_mode, parent,
                )

            # DB file: rw------- (600) — only if it exists
            if self._db_path.exists():
                current_file_mode = self._db_path.stat().st_mode & 0o777
                if current_file_mode != 0o600:
                    os.chmod(self._db_path, 0o600)
                    logger.info(
                        "SECURITY: Fixed DB perms %o → 600 on %s",
                        current_file_mode, self._db_path,
                    )
        except OSError as e:
            logger.warning("SECURITY: Could not enforce permissions: %s", e)

    # ─── Security: CLI Audit Trail ────────────────────────────────

    @staticmethod
    def _audit_log(
        action: str, fact_type: str = "",
        project: str = "", tenant_id: str = "default",
    ) -> None:
        """Append-only audit log for CLI/SDK access to CORTEX memory."""
        audit_logger = logging.getLogger("cortex.audit")
        audit_logger.info(
            "AUDIT: action=%s fact_type=%s project=%s tenant=%s",
            action, fact_type, project, tenant_id,
        )

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

            # Ensure memory subsystem is initialized (L1/L2/L3)
            # This is critical for Active Forgetting (Thalamus Gate)
            if self._memory_manager is None:
                await self._init_memory_subsystem(self._db_path, self._conn)

            return self._conn

    def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Connection not initialized. Call get_conn() first.")
        return self._conn

    def get_connection(self) -> aiosqlite.Connection:
        return self.get_conn()

    def _get_sync_conn(self):
        """Devuelve una conexión síncrona para procesos bloqueantes."""
        from cortex.database.core import connect
        import sqlite3

        conn = connect(str(self._db_path), row_factory=sqlite3.Row)
        conn.enable_load_extension(True)
        try:
            conn.load_extension(sqlite_vec.loadable_path())
        except AttributeError:
            pass
        conn.enable_load_extension(False)
        return conn

    # ─── Synchronous Wrappers (SDK Parity) ────────────────────────

    def _run_sync(self, coro):
        """Execute a coroutine synchronously, thread-safe."""
        import threading

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result = None
        exception = None

        def _worker():
            nonlocal result, exception
            try:
                result = asyncio.run(coro)
            except Exception as e:
                exception = e

        t = threading.Thread(target=_worker)
        t.start()
        t.join()
        if exception:
            raise exception
        return result

    def init_db_sync(self) -> None:
        return self._run_sync(self.init_db())

    def store_sync(self, *args, **kwargs):
        return self._run_sync(self.store(*args, **kwargs))

    def recall_sync(self, *args, **kwargs):
        return self._run_sync(self.recall(*args, **kwargs))

    def search_sync(self, *args, **kwargs):
        return self._run_sync(self.search(*args, **kwargs))

    def hybrid_search_sync(self, *args, **kwargs):
        return self._run_sync(self.search(*args, **kwargs))

    def close_sync(self):
        return self._run_sync(self.close())

    # ─── Backward Compatibility Aliases & Delegation ──────────────

    async def store(self, *args, **kwargs):
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)

    async def store_many(self, *args, **kwargs):
        return await self.facts.store_many(*args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self.facts.search(*args, **kwargs)

    async def recall(self, *args, **kwargs):
        self._audit_log(
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
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

    async def shannon_report(self, project: str | None = None) -> dict:
        """Shannon entropy analysis of stored memory."""
        from cortex.shannon.report import EntropyReport

        return await EntropyReport.analyze(self, project)

    async def prioritize(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list:
        """Bellman Policy Engine — prioritized action queue.

        Returns a list of ActionItems scored by value function V(s) = R(s,a) + γ·V(s').
        Higher value = more urgent/impactful action.
        """
        from cortex.policy import PolicyEngine

        policy = PolicyEngine(self)
        return await policy.evaluate(project=project, tenant_id=tenant_id)

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
