"""CORTEX Engine — Package init."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite
import sqlite_vec

from cortex.config import DEFAULT_DB_PATH
from cortex.database.schema import get_init_meta
from cortex.embeddings import LocalEmbedder
from cortex.engine.durability import PersistenceSupervisor
from cortex.engine.memory_mixin import MemoryMixin
from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.models import row_to_fact  # noqa: F401 — re-exported
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.transaction_mixin import TransactionMixin

try:
    from cortex.extensions.health.health_mixin import HealthMixin  # type: ignore
except ImportError:

    class HealthMixin:  # type: ignore
        async def health_check(self, *args, **kwargs):
            return {"status": "unhealthy", "reason": "No Health extension"}

        async def health_report(self, *args, **kwargs):
            return {"status": "unhealthy", "reason": "No Health extension"}


from cortex.migrations.core import run_migrations_async
from cortex.telemetry.metrics import metrics

logger = logging.getLogger("cortex")


from cortex.consensus.manager import ConsensusManager  # noqa: E402
from cortex.embeddings.manager import EmbeddingManager  # noqa: E402
from cortex.engine.compound_yield import CompoundReport, CompoundYieldTracker  # noqa: E402
from cortex.engine.lock import SovereignLock  # noqa: E402
from cortex.facts.manager import FactManager  # noqa: E402

if TYPE_CHECKING:
    from cortex.extensions.interfaces.engine import EngineProtocol

# Limit the maximum number of tags per fact.
MAX_TAGS_PER_FACT = 20

# We use the unified GuardPipeline for AX-033 logic.


class CortexEngine(
    StoreMixin,
    QueryMixin,
    MemoryMixin,
    TransactionMixin,
    HealthMixin,
):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        super().__init__()
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
        self._persistence = PersistenceSupervisor(self)

        # Composition layers
        self.facts = FactManager(self)
        self.embeddings = EmbeddingManager(self)
        self.consensus = ConsensusManager(self)
        self.lock_sovereign = SovereignLock(self)

        # Decoupled guard pipeline (Ω₃: minimal coupling)
        self._guard_pipeline = self._register_default_guards()

    # ─── Guard Pipeline Registration ──────────────────────────────

    def _register_default_guards(self):
        """Build the GuardPipeline with all available guard adapters.

        Each adapter is imported defensively — if the underlying module
        is not installed, the adapter is silently skipped. This ensures
        the engine always starts, regardless of optional dependencies.
        """
        from cortex.engine.guard_pipeline import GuardPipeline

        pipeline = GuardPipeline()
        db_path = str(self._db_path)

        # Pre-store guards (AX-033 Hooks 1-3)
        try:
            from cortex.engine.guard_adapters import HealthGuardAdapter

            pipeline.add_guard(HealthGuardAdapter(db_path))
        except (ImportError, Exception):  # noqa: BLE001
            pass

        try:
            from cortex.engine.guard_adapters import ContradictionGuardAdapter

            pipeline.add_guard(ContradictionGuardAdapter(db_path))
        except (ImportError, Exception):  # noqa: BLE001
            pass

        try:
            from cortex.engine.guard_adapters import VerifierGuardAdapter

            pipeline.add_guard(VerifierGuardAdapter())
        except (ImportError, Exception):  # noqa: BLE001
            pass

        # Post-store hooks (AX-033 Hook 4 + signals + epistemic)
        try:
            from cortex.engine.guard_adapters import LedgerCheckpointHook

            pipeline.add_post_hook(LedgerCheckpointHook(self))
        except (ImportError, Exception):  # noqa: BLE001
            pass

        try:
            from cortex.engine.guard_adapters import SignalEmitHook

            pipeline.add_post_hook(SignalEmitHook())
        except (ImportError, Exception):  # noqa: BLE001
            pass

        try:
            from cortex.engine.guard_adapters import EpistemicBreakerHook

            pipeline.add_post_hook(EpistemicBreakerHook())
        except (ImportError, Exception):  # noqa: BLE001
            pass

        logger.debug(
            "GuardPipeline: %d guards, %d hooks registered",
            pipeline.guard_count,
            pipeline.hook_count,
        )
        return pipeline

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
                    current_dir_mode,
                    parent,
                )

            # DB file: rw------- (600) — only if it exists
            if self._db_path.exists():
                current_file_mode = self._db_path.stat().st_mode & 0o777
                if current_file_mode != 0o600:
                    os.chmod(self._db_path, 0o600)
                    logger.info(
                        "SECURITY: Fixed DB perms %o → 600 on %s",
                        current_file_mode,
                        self._db_path,
                    )
        except OSError as e:
            logger.warning("SECURITY: Could not enforce permissions: %s", e)

    # ─── Security: CLI Audit Trail ────────────────────────────────

    @staticmethod
    def _audit_log(
        action: str,
        fact_type: str = "",
        project: str = "",
        tenant_id: str = "default",
    ) -> None:
        """Append-only audit log for CLI/SDK access to CORTEX memory."""
        audit_logger = logging.getLogger("cortex.audit")
        audit_logger.info(
            "AUDIT: action=%s fact_type=%s project=%s tenant=%s",
            action,
            fact_type,
            project,
            tenant_id,
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
        return self.get_conn()  # type: ignore[reportReturnType]

    def _get_sync_conn(self):
        """Devuelve una conexión síncrona para procesos bloqueantes."""
        import sqlite3

        from cortex.database.core import connect

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
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # noqa: BLE001 — sync wrapper must catch all async errors to propagate
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

    # ─── Causal Episode Tracing (Epoch 8) ─────────────────────────

    async def recall_episode(
        self,
        query: str,
        project: str = "",
        limit: int = 3,
    ) -> list:
        """Recall causal episodes matching a query.

        Returns full causal DAGs, not isolated facts.
        Enables the LLM to understand *why* something happened.
        """
        from cortex.memory.episodic import CausalTracer

        conn = await self.get_conn()
        tracer = CausalTracer(conn)
        return await tracer.recall_episode(query, project, limit)

    async def trace_episode(
        self,
        fact_id: int,
        max_depth: int | None = None,
    ):
        """Trace the full causal DAG from a given fact ID."""
        from cortex.memory.episodic import CausalTracer

        conn = await self.get_conn()
        tracer = CausalTracer(conn)
        return await tracer.trace_episode(fact_id, max_depth)

    def recall_episode_sync(self, *args, **kwargs):
        return self._run_sync(self.recall_episode(*args, **kwargs))

    def trace_episode_sync(self, *args, **kwargs):
        return self._run_sync(self.trace_episode(*args, **kwargs))

    def graph_sync(self, *args, **kwargs):
        return self._run_sync(self.graph(*args, **kwargs))

    def query_entity_sync(self, *args, **kwargs):
        return self._run_sync(self.query_entity(*args, **kwargs))

    def get_causal_chain_sync(self, *args, **kwargs):
        return self._run_sync(self.get_causal_chain(*args, **kwargs))

    def close_sync(self):
        return self._run_sync(self.close())

    def health_check_sync(self, *args, **kwargs):
        return self._run_sync(self.health_check(*args, **kwargs))

    def health_report_sync(self, *args, **kwargs):
        return self._run_sync(self.health_report(*args, **kwargs))

    # ─── Backward Compatibility Aliases & Delegation ──────────────

    async def store(self, *args, **kwargs):
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)

    async def store_many(self, *args, **kwargs):
        return await super().store_many(*args, **kwargs)

    async def recall(self, *args, **kwargs):
        self._audit_log(
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await super().recall(*args, **kwargs)

    async def get_fact(self, *args, **kwargs):
        res = await super().get_fact(*args, **kwargs)
        if not res:
            return None
        from cortex.engine.models import Fact

        return Fact(**{k: v for k, v in res.items() if k in Fact.__dataclass_fields__})

    async def retrieve(self, fact_id: int):
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        from cortex.utils.errors import FactNotFound

        conn = await self.get_conn()
        async with conn.execute(
            f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ?", (fact_id,)
        ) as cursor:
            row = await cursor.fetchone()
        fact = row_to_fact(row) if row else None  # type: ignore[reportArgumentType]
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def vote(self, *args, **kwargs):
        return await self.consensus.vote(*args, **kwargs)

    async def get_all_active_facts(self, *args, **kwargs):
        """Retrieve all active facts across all projects, wrapped in models."""
        results = await super().get_all_active_facts(*args, **kwargs)
        from cortex.engine.models import Fact

        return [Fact(**{k: v for k, v in r.items() if k != "type"}) for r in results]

    async def shannon_report(self, project: str | None = None) -> dict:
        """Shannon entropy analysis of stored memory."""
        from cortex.extensions.shannon.report import EntropyReport

        return await EntropyReport.analyze(self, project)

    async def fingerprint(
        self,
        project: str | None = None,
        top_domains: int = 15,
    ):
        """Cognitive Fingerprint — extract behavioral patterns from the Ledger.

        Returns a CognitiveFingerprint with:
        - PatternVector: 7 behavioral dimensions (risk, caution, synthesis…)
        - DomainPreferences: top active (project × fact_type) signatures
        - Archetype: sovereign_architect / obsessive_executor / etc.
        - to_agent_prompt(): ready for LLM system prompt injection

        Args:
            project: Optional project filter.
            top_domains: Max domain preferences to extract.
        """
        from cortex.extensions.fingerprint.extractor import FingerprintExtractor

        return await FingerprintExtractor.extract(self, project, top_domains)

    def fingerprint_sync(self, *args, **kwargs):
        return self._run_sync(self.fingerprint(*args, **kwargs))

    async def immortality_index(self, project: str | None = None) -> dict:
        """Immortality Index (ι) — cognitive crystallization metric."""
        from cortex.extensions.shannon.immortality import ImmortalityIndex

        return await ImmortalityIndex.compute(self, project)

    def immortality_index_sync(self, *args, **kwargs):
        return self._run_sync(self.immortality_index(*args, **kwargs))

    async def prioritize(
        self,
        project: str | None = None,
        tenant_id: str = "default",
    ) -> list:
        """Bellman Policy Engine — prioritized action queue.

        Returns a list of ActionItems scored by value function V(s) = R(s,a) + γ·V(s').
        Higher value = more urgent/impactful action.
        """
        from cortex.extensions.policy import PolicyEngine

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

        self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
        await self._init_memory_subsystem(self._db_path, conn)
        await self._persistence.start()
        metrics.set_engine(self)
        logger.info("CORTEX database initialized (async) at %s", self._db_path)

    # ─── Helpers ──────────────────────────────────────────────────

    def export_snapshot(self, out_path: str | Path) -> str:
        # Note: export_snapshot itself might be sync/blocking, consider if it needs move or refactor
        from cortex.extensions.sync.snapshot import export_snapshot

        return export_snapshot(self, out_path)  # type: ignore[reportArgumentType,reportReturnType]

    def _row_to_fact(  # type: ignore[override]
        self,
        row: aiosqlite.Row | dict,
        tenant_id: str = "default",
    ) -> dict:
        """Delegate to MixinBase (supports tenant-scoped decryption)."""
        return super()._row_to_fact(  # type: ignore[reportAttributeAccessIssue]
            row,
            tenant_id=tenant_id,
        )

    # ─── Lifecycle ────────────────────────────────────────────────

    async def close(self):
        if self._memory_manager:
            try:
                await asyncio.wait_for(
                    self._memory_manager.wait_for_background(),  # type: ignore
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Memory manager background drain timed out — forcing close")
            self._memory_manager = None
        if self._persistence:
            await self._persistence.stop()
        if self._conn:
            await self._conn.close()
            self._conn = None
        self._ledger = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
