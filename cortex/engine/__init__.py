"""CORTEX Engine — Package init."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite
import sqlite_vec

if TYPE_CHECKING:
    pass

from cortex.config import DEFAULT_DB_PATH
from cortex.database.schema import get_init_meta
from cortex.embeddings import LocalEmbedder
from cortex.engine.durability import PersistenceSupervisor
from cortex.engine.memory_mixin import MemoryMixin
from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.mixins.optimization import OptimizationMixin
from cortex.engine.models import row_to_fact  # noqa: F401 — re-exported
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.search_mixin import SearchMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.transaction_mixin import TransactionMixin
from cortex.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
from cortex.mac_maestro.executor import MaestroExecutor

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

logger = logging.getLogger("cortex.engine.guards")


from cortex.consensus.manager import ConsensusManager  # noqa: E402
from cortex.embeddings.manager import EmbeddingManager  # noqa: E402
from cortex.engine.lock import SovereignLock  # noqa: E402

# Limit the maximum number of tags per fact.
MAX_TAGS_PER_FACT = 20

# We use the unified GuardPipeline for AX-II logic.


class CortexEngine(
    SearchMixin,
    StoreMixin,
    QueryMixin,
    MemoryMixin,
    TransactionMixin,
    OptimizationMixin,
    HealthMixin,
):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self,
        db_path: str | Path | Any = DEFAULT_DB_PATH,
        auto_embed: bool = True,
        pool: Any = None,
    ):
        # Initialize mixins
        SearchMixin.__init__(self)
        StoreMixin.__init__(self)
        QueryMixin.__init__(self)
        MemoryMixin.__init__(self)
        TransactionMixin.__init__(self)
        OptimizationMixin.__init__(self)
        HealthMixin.__init__(self)
        # Handle argument inversion from tests if necessary (pool, db_path)
        if hasattr(db_path, "acquire") and not isinstance(db_path, (str, Path)):
            self._pool = db_path
            self._db_path = Path(str(auto_embed)).expanduser()
            self._auto_embed = True
        else:
            self._db_path = Path(str(db_path)).expanduser()
            self._auto_embed = auto_embed
            self._pool = pool

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._enforce_fs_permissions()
        self._conn: aiosqlite.Connection | None = None
        self._vec_available = False
        self._conn_lock = asyncio.Lock()
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)
        self._embedder: LocalEmbedder | None = None
        self._memory_manager = None  # Frontera 2: Tripartite Memory (lazy init)
        self._persistence = PersistenceSupervisor(self)
        self._system_state = "ACTIVE"

        # Composition layers
        from cortex.facts.manager import FactManager

        self.facts = FactManager(self)  # pyright: ignore
        self.embeddings = EmbeddingManager(self)
        self.consensus = ConsensusManager(self)
        self.lock_sovereign = SovereignLock(self)

        # Wave 6: Sovereign Ledger Integration
        self.ledger_store = LedgerStore(self._db_path)
        self.enrichment_queue = EnrichmentQueue(self.ledger_store)
        self.ledger_writer = LedgerWriter(self.ledger_store, self.enrichment_queue)
        self.mac_maestro = MaestroExecutor(self.ledger_writer)
        from cortex.engine.auth import ByzantineAuthLayer

        self.auth = ByzantineAuthLayer()

        # Decoupled guard pipeline (Ω₃: minimal coupling)
        self._guard_pipeline = self._register_default_guards()

    # ─── System State ─────────────────────────────────────────────────────────

    @property
    def system_state(self) -> str:
        return self._system_state

    def set_system_state(self, state: str) -> None:
        """Lock or unlock the sovereign engine (e.g., from EpistemicCircuitBreaker)"""
        self._system_state = state
        logger.warning("🛡️ [SOVEREIGN-STATE] CORTEX Engine state changed to: %s", state)

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
        import os  # Local import to resolve persistent pylint/ruff shadowing issues

        # Pre-store guards (AX-II Hooks 1-3)
        try:
            from cortex.engine.guard_adapters import HealthGuardAdapter

            pipeline.add_guard(HealthGuardAdapter(db_path))
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: HealthGuardAdapter failed: {e}") from e
            pass

        try:
            from cortex.engine.guard_adapters import ContradictionGuardAdapter

            pipeline.add_guard(ContradictionGuardAdapter(db_path))
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ContradictionGuardAdapter failed: {e}") from e
            pass

        try:
            from cortex.engine.guard_adapters import VerifierGuardAdapter

            pipeline.add_guard(VerifierGuardAdapter())
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: VerifierGuardAdapter failed: {e}") from e
            pass

        # Post-store hooks (AX-II Hook 4 + signals + epistemic)
        try:
            from cortex.engine.guard_adapters import LedgerCheckpointHook

            pipeline.add_post_hook(LedgerCheckpointHook(self))
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: LedgerCheckpointHook failed: {e}") from e
            pass

        try:
            from cortex.engine.guard_adapters import SignalEmitHook

            pipeline.add_post_hook(SignalEmitHook())
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: SignalEmitHook failed: {e}") from e
            pass

        try:
            from cortex.engine.guard_adapters import EpistemicBreakerHook

            pipeline.add_post_hook(EpistemicBreakerHook())
        except (ImportError, Exception) as e:  # noqa: BLE001
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: EpistemicBreakerHook failed: {e}") from e
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
        # If we have an injected pool (from tests), use its context manager
        if hasattr(self, "_pool") and self._pool is not None:
            async with self._pool.acquire() as conn:
                yield conn
        else:
            conn = await self._get_or_create_conn()
            yield conn

    def _get_embedder(self) -> LocalEmbedder:
        """Protocol requirement for SearchMixin."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Connection ───────────────────────────────────────────────

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns the async database connection.
        DEPRECATED: Use 'async with engine.session() as conn:' instead.
        """
        import warnings

        warnings.warn(
            "get_conn() is deprecated. Use session() context manager.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self._get_or_create_conn()

    async def _get_conn(self) -> aiosqlite.Connection:
        """Internal helper for connection acquisition (deprecated alias)."""
        return await self._get_or_create_conn()

    async def _get_or_create_conn(self) -> aiosqlite.Connection:
        """Internal helper for connection acquisition.
        Note: This path is for single-connection mode.
        """
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

    def get_connection(self) -> aiosqlite.Connection:
        """Synchronous wrapper for internal connection access."""
        if self._conn is None:
            raise RuntimeError("Connection not initialized. Call session() first.")
        return self._conn

    def _get_sync_conn(self):
        """Devuelve una conexión síncrona para procesos bloqueantes."""
        import sqlite3

        from cortex.database.core import connect

        conn = connect(str(self._db_path), row_factory=sqlite3.Row)
        try:
            conn.enable_load_extension(True)
            conn.load_extension(sqlite_vec.loadable_path())
            conn.enable_load_extension(False)
        except (AttributeError, OSError):
            pass  # System Python lacks extension loading
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
        """
        from cortex.memory.episodic import CausalTracer

        async with self.session() as conn:
            tracer = CausalTracer(conn)
            return await tracer.recall_episode(query, project, limit)

    async def trace_episode(
        self,
        fact_id: int,
        max_depth: int | None = None,
    ):
        """Trace the full causal DAG from a given fact ID."""
        from cortex.memory.episodic import CausalTracer

        async with self.session() as conn:
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

    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        res = await super().get_fact(fact_id, tenant_id=tenant_id)
        if not res:
            return None
        from cortex.engine.models import Fact

        return Fact(**{k: v for k, v in res.items() if k in Fact.__dataclass_fields__})

    async def retrieve(self, fact_id: int):
        """Retrieve an active fact. Raises FactNotFound if missing or deprecated."""
        from cortex.utils.errors import FactNotFound

        async with self.session() as conn:
            async with conn.execute(
                f"SELECT {FACT_COLUMNS} {FACT_JOIN} WHERE f.id = ?", (fact_id,)
            ) as cursor:
                row = await cursor.fetchone()
        fact = row_to_fact(tuple(row)) if row else None
        if not fact or fact.valid_until:
            raise FactNotFound(f"Fact {fact_id} not found or deprecated")
        return fact

    async def vote_v2(self, *args, **kwargs):
        return await self.consensus.vote_v2(*args, **kwargs)

    async def get_all_active_facts(self, *args, **kwargs):
        """Retrieve all active facts across all projects, wrapped in models."""
        results = await super().get_all_active_facts(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def history(self, *args, **kwargs):
        """Retrieve historical facts wrapped in models."""
        results = await super().history(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

    async def get_causal_chain(self, *args, **kwargs):
        """Retrieve causal chain facts wrapped in models."""
        results = await super().get_causal_chain(*args, **kwargs)
        from cortex.engine.models import Fact

        return [
            Fact(**{k: v for k, v in r.items() if k in Fact.__dataclass_fields__}) for r in results
        ]

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
        """Bellman Policy Engine — prioritized action queue."""
        from cortex.extensions.policy import PolicyEngine

        policy = PolicyEngine(self)
        return await policy.evaluate(project=project, tenant_id=tenant_id)

    # ─── Schema ───────────────────────────────────────────────────

    async def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        from cortex.database.schema import get_all_schema
        from cortex.ledger import ImmutableLedger

        async with self.session() as conn:
            # Explicitly run migrations BEFORE initialization meta to preserve order logic
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

    async def start(self):
        """Ignite the sovereign engine and its optimization layers."""
        await self.start_optimizer()
        await self._persistence.start()
        logger.info("🚀 [CORTEX] Sovereign Engine ignited (Ω₀-Ω₆).")

    async def close(self):
        """Shutdown the engine, optimizer, and database connections."""
        await self.stop_optimizer()
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

        # Clean up Wave 6 references
        self.mac_maestro = None  # type: ignore
        self.ledger_writer = None  # type: ignore
        self.enrichment_queue = None  # type: ignore
        self.ledger_store = None  # type: ignore

        self._ledger = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


# Ω₀ Type Alias for backward compatibility (AX-V Refactor)
AsyncCortexEngine = CortexEngine
