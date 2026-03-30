"""CORTEX Engine — Package init."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite
import sqlite_vec

from cortex.config import DEFAULT_DB_PATH
from cortex.daemon.chaos import ChaosDaemon
from cortex.daemon.maxwell import MaxwellDaemon
from cortex.database.pool import CortexConnectionPool
from cortex.database.schema import get_init_meta
from cortex.database.soul_store import SoulStore
from cortex.database.writer import SqliteWriteWorker
from cortex.embeddings import LocalEmbedder
from cortex.engine.agent_mixin import AgentMixin

# Frontera x10: Kinetic Engines & Daemons
from cortex.engine.annihilator import AnnihilatorEngine
from cortex.engine.bicameral import OaxacaEngine
from cortex.engine.consensus import ConsensusMixin
from cortex.engine.crystallizer import CrystallizerJIT as CausalCrystallizer
from cortex.engine.durability import PersistenceSupervisor
from cortex.engine.ghost_mixin import GhostMixin
from cortex.engine.history import HistoryMixin
from cortex.engine.isolation import ByzantineSandbox, IsolationManager
from cortex.engine.evolution import EvolutionEngine
from cortex.engine.memory_mixin import MemoryMixin
from cortex.engine.pearl import PearlEngine
from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.mixins.bicameral_mixin import BicameralMixin
from cortex.engine.models import row_to_fact  # noqa: F401 — re-exported
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.search_mixin import SearchMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.transaction_mixin import TransactionMixin
from cortex.identity.alma import AlmaIdentity
from cortex.ledger.compaction import ShannonCompactor
from cortex.ops.git_ledger import GitLedgerOps
from cortex.ops.kv_router import KVAwareRouter
from cortex.utils.result import Err, Ok, Result

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
from cortex.extensions.x_intelligence.daemon import XIntelligenceDaemon  # noqa: E402
from cortex.facts.manager import FactManager  # noqa: E402

if TYPE_CHECKING:
    from cortex.extensions.interfaces.engine import EngineProtocol

# Limit the maximum number of tags per fact.
MAX_TAGS_PER_FACT = 20

# We use the unified GuardPipeline for AX-033 logic.


class CortexEngine(
    SearchMixin,
    StoreMixin,
    GhostMixin,
    QueryMixin,
    MemoryMixin,
    TransactionMixin,
    BicameralMixin,
    HealthMixin,
    AgentMixin,
    ConsensusMixin,
    HistoryMixin,
):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
        pool: CortexConnectionPool | None = None,
        writer: SqliteWriteWorker | None = None,
    ):
        super().__init__()
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._pool = pool
        self._writer = writer
        self._conn: aiosqlite.Connection | None = None

        self._vec_available = False
        try:
            import sqlite_vec as _

            self._vec_available = True
        except ImportError:
            pass

        self._conn_lock = asyncio.Lock()
        self._ledger = None  # Wave 5: SovereignLedger (lazy init)
        self._embedder: LocalEmbedder | None = None
        self._memory_manager = None  # Frontera 2: Tripartite Memory (lazy init)
        self._persistence = PersistenceSupervisor(self)
        self._x_daemon_task: asyncio.Task | None = None
        self._memento_agent: Any | None = None
        self._closed = False

        # Composition layers
        self.facts = FactManager(self)
        self.embeddings = EmbeddingManager(self)
        self.consensus = ConsensusManager(self)
        self.lock_sovereign = SovereignLock(self)
        self.isolation = IsolationManager(self)
        self.sandbox = ByzantineSandbox(self.isolation)

        # Ω₁₃: Shannon Compactor (Thermodynamic Memory Hygiene)
        self.shannon = ShannonCompactor(self)

        # 🐝 Swarm High Command (Ω₄)
        try:
            from cortex.swarm.factory import SwarmFactory
            from cortex.swarm.manager import SwarmManager

            self.manager = SwarmManager(self)
            self.factory = SwarmFactory(self.manager)
        except ImportError:
            logger.warning("Swarm Orchestrator not available. Frontier systems limited.")
            self.manager = None
            self.factory = None

        # Ω₁₃: X-Intelligence Daemon (Autonomous Signal Monitor)
        self.x_daemon = XIntelligenceDaemon()
        if self.manager:
            self.x_daemon.set_bus(self.manager.bus)

        # Decoupled guard pipeline (Ω₃: minimal coupling)
        self._guard_pipeline = self._register_default_guards()

        # Ω₁: Identity & Soul (Apotheosis Core)
        self._alma = AlmaIdentity(self._db_path.parent / "alma.json")
        self._soul_store = SoulStore()

        # Initialize Bicameral Routes (v8.0)
        self._setup_bicameral_performance_routes()

        # Frontera x10: Kinetic Engines
        self.annihilator = AnnihilatorEngine(self, self._db_path.parent)
        self.crystallizer = CausalCrystallizer(self._db_path.parent)

        # Frontera x10: Background Daemons
        self.chaos_daemon = ChaosDaemon(self)
        self.maxwell_daemon = MaxwellDaemon(self)

        # Frontera x10: Sovereign Operations
        self.git_ops = GitLedgerOps(self, self._db_path.parent)
        self.kv_router = KVAwareRouter(self)

        # Ω₁₃: PeARL & Evolution Engines (AX-043, AX-048)
        self.pearl = PearlEngine()
        self.evolution = EvolutionEngine(self.pearl)

    def _setup_bicameral_performance_routes(self):
        """Internal wiring for the high-performance dual bus."""
        self.dispatcher.register_fast("search", self.search)

        # 🟡 Slow Path: Persistence & Audit (IO-intensive + Apotheosis Verification)
        self.dispatcher.register_slow(self._apotheosis_store)

    async def _apotheosis_store(self, *args, **kwargs) -> int:
        """Unified store with Soul Integrity verification (Ω₁)."""
        # Extract project from args/kwargs
        project = kwargs.get("project", args[0] if args else "default")

        # Verify Alma before any write
        await self.alma.verify_soul_integrity(project)

        # If it's a soul record, persist to soul store
        if kwargs.get("fact_type") == "soul":
            # Assuming 'content' is the soul data (dict or str)
            content = kwargs.get("content", args[1] if len(args) > 1 else None)
            if content:
                # Alma already verified, now persist to soul store
                async with self.session() as conn:
                    await self.soul.save_pulse(conn, payload=content, tenant_id=project)

        # Standard persistence (delegates to FactManager)
        return await self.facts.store(*args, **kwargs)

    @property
    def memory(self) -> Any:
        """Access the tripartite memory layer."""
        return self._memory_manager

    @property
    def ledger(self) -> Any:
        """Access the unified Sovereign Ledger."""
        return self._ledger

    @property
    def soul(self) -> SoulStore:
        """Access the Soul Store (Ω₁)."""
        return self._soul_store

    @property
    def alma(self) -> AlmaIdentity:
        """Access the Alma Identity (Root of Trust)."""
        return self._alma

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
        # Fail-close: only catch ImportError for optional deps.
        # Any other exception (bad guard init) propagates to crash the engine.
        try:
            from cortex.engine.guard_adapters import ExergyGuardAdapter

            exergy_adapter = ExergyGuardAdapter()
            pipeline.add_mutator(exergy_adapter)
        except ImportError:
            logger.debug("ExergyGuardAdapter not available — skipping")

        try:
            from cortex.engine.guard_adapters import HealthGuardAdapter

            pipeline.add_guard(HealthGuardAdapter(db_path))
        except ImportError:
            logger.debug("HealthGuardAdapter not available — skipping")

        try:
            from cortex.engine.guard_adapters import ContradictionGuardAdapter

            pipeline.add_guard(ContradictionGuardAdapter(db_path))
        except ImportError:
            logger.debug("ContradictionGuardAdapter not available — skipping")

        try:
            from cortex.engine.guard_adapters import VerifierGuardAdapter

            pipeline.add_guard(VerifierGuardAdapter())
        except ImportError:
            logger.debug("VerifierGuardAdapter not available — skipping")

        try:
            from cortex.engine.guard_adapters import XForensicGuardAdapter

            pipeline.add_guard(XForensicGuardAdapter())
        except ImportError:
            logger.debug("XForensicGuardAdapter not available — skipping")

        try:
            from cortex.engine.guard_adapters import FEPMoravecGuardAdapter

            pipeline.add_guard(FEPMoravecGuardAdapter())
        except ImportError:
            logger.debug("FEPMoravecGuardAdapter not available — skipping")

        # Post-store hooks (AX-033 Hook 4 + signals + epistemic)
        try:
            from cortex.engine.guard_adapters import LedgerCheckpointHook

            pipeline.add_post_hook(LedgerCheckpointHook(self))
        except ImportError:
            logger.debug("LedgerCheckpointHook not available — skipping")

        try:
            from cortex.engine.guard_adapters import SignalEmitHook

            pipeline.add_post_hook(SignalEmitHook())
        except ImportError:
            logger.debug("SignalEmitHook not available — skipping")

        try:
            from cortex.engine.guard_adapters import EpistemicBreakerHook

            pipeline.add_post_hook(EpistemicBreakerHook())
        except ImportError:
            logger.debug("EpistemicBreakerHook not available — skipping")

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

    async def write(self, sql: str, params: tuple[Any, ...] = ()) -> Result[int, str]:
        """Unified write entry point with worker support and failover retries."""
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
        return Err("Cortex write error: Exceeded max retries for DB Lock.")

    async def _try_execute_write(
        self, sql: str, params: tuple[Any, ...], attempt: int, max_retries: int
    ) -> Result[int, str] | None:
        try:
            return await self._execute_write(sql, params)
        except (sqlite3.Error, OSError) as e:
            if "database is locked" not in str(e).lower() or attempt >= max_retries:
                return Err(f"Cortex write error: {e}")
            await self._backoff(attempt)
        return None

    async def _execute_write(self, sql: str, params: tuple[Any, ...]) -> Result[int, str]:
        async with self.session() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            if sql.strip().upper().startswith("INSERT"):
                return Ok(cursor.lastrowid)  # type: ignore[reportReturnType]
            return Ok(cursor.rowcount)

    async def _backoff(self, attempt: int):
        import random

        sleep_time = (0.5 * (3**attempt)) + random.uniform(0.1, 0.5)
        logger.warning(
            "WAL Locked: Backing off %.2fs (attempt %d/3)...",
            sleep_time,
            attempt + 1,
        )
        await asyncio.sleep(sleep_time)

    @asynccontextmanager
    async def session(self, read_only: bool = False) -> AsyncIterator[aiosqlite.Connection]:
        """Proporciona una sesión transaccional (conexión) válida.

        Axioma Ω₁₃: Aislamiento de flujo. Cada tarea asíncrona obtiene su propia conexión
        para evitar colisiones de transacciones 'nested' en el mismo handle de SQLite.
        """
        if self._closed:
            raise RuntimeError("CortexEngine is closed")

        # Detect URI mode to prevent root directory pollution (file:mem_ ghost files)
        is_uri = str(self._db_path).startswith("file:") or "mode=memory" in str(self._db_path)

        if self._pool:
            async with self._pool.acquire() as conn:
                try:
                    yield conn
                except Exception:
                    try:
                        await conn.rollback()
                    except Exception:  # noqa: BLE001
                        pass
                    raise
            return

        from cortex.database.core import connect_async

        conn = await connect_async(str(self._db_path), uri=is_uri, read_only=read_only)
        try:
            yield conn
        except Exception:
            try:
                await conn.rollback()
            except Exception:  # noqa: BLE001
                pass
            raise
        finally:
            await conn.close()

    def _get_embedder(self) -> LocalEmbedder:
        """Protocol requirement for SearchMixin."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Connection ───────────────────────────────────────────────

    async def get_conn(self) -> aiosqlite.Connection:
        """Returns an async connection.
        WARNING: Defaulting to a singleton connection is deprecated due to concurrency risks.
        Use 'async with engine.session()' instead.
        """
        is_uri = str(self._db_path).startswith("file:") or "mode=memory" in str(self._db_path)
        from cortex.database.core import connect_async

        return await connect_async(str(self._db_path), uri=is_uri)

    def _get_conn(self) -> aiosqlite.Connection:
        """Deprecated: accessing internal connection singleton is unsafe."""
        if self._conn is None:
            # Fallback for legacy mixins that haven't moved to session() yet
            # This should be avoided in new code.
            raise RuntimeError(
                "Connection singleton not initialized. Use session() context manager."
            )
        return self._conn

    def get_connection(self) -> aiosqlite.Connection:
        """Alias for get_conn for legacy compatibility."""
        return asyncio.run(self.get_conn())  # type: ignore[reportReturnType]

    def get_conn_sync(self) -> sqlite3.Connection:
        """Devuelve una conexión síncrona para procesos bloqueantes."""
        from cortex.database.core import connect

        is_uri = str(self._db_path).startswith("file:") or "mode=memory" in str(self._db_path)
        conn = connect(str(self._db_path), row_factory=sqlite3.Row, uri=is_uri)
        try:
            conn.enable_load_extension(True)
            conn.load_extension(sqlite_vec.loadable_path())
            conn.enable_load_extension(False)
        except (AttributeError, OSError):
            pass  # System Python lacks extension loading
        return conn

    def _get_sync_conn(self) -> sqlite3.Connection:
        """Alias for get_conn_sync — satisfies EngineMixinBase contract."""
        return self.get_conn_sync()

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
        tracer = CausalTracer(conn, self)
        return await tracer.recall_episode(query, project, limit)

    async def trace_episode(
        self,
        fact_id: int,
        max_depth: int | None = None,
    ):
        """Trace the full causal DAG from a given fact ID."""
        from cortex.memory.episodic import CausalTracer

        conn = await self.get_conn()
        tracer = CausalTracer(conn, self)
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
        """Unified store entry point.

        Ω₃: Routes through the BicameralDispatcher (Dual Bus) to ensure
        high-performance persistence and thermodynamic auditability.
        """
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )

        # Determine if we should use the fast path or the standard path.
        # AX-034: All writes must be verifiable and auditable.
        if hasattr(self, "dispatcher") and self.dispatcher:
            # We route 'store' through the dispatcher.
            # If it's a slow-path operation (persistence), it will be handled by the slow bus.
            return await self.dispatcher.dispatch("store", *args, **kwargs)

        return await self.facts.store(*args, **kwargs)

    async def store_direct(self, *args, **kwargs):
        """Persist a fact without re-entering the public dispatcher."""
        return await StoreMixin.store(self, *args, **kwargs)

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
        from cortex.ledger.sovereign_ledger import SovereignLedger

        async with self.session() as conn:
            await run_migrations_async(conn)

            for k, v in get_init_meta():
                await conn.execute(
                    "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                    (k, v),
                )
            await conn.commit()

            self._ledger = SovereignLedger(self._pool or self)  # type: ignore[reportArgumentType]
            self.shannon = ShannonCompactor(conn)
            await self._init_memory_subsystem(self._db_path, conn)

            if not os.environ.get("CORTEX_TESTING"):
                # Start X-Intelligence Daemon in the background (Ω₁₃)
                if not self._x_daemon_task or self._x_daemon_task.done():
                    self._x_daemon_task = asyncio.create_task(
                        self.x_daemon.start_loop(), name="cortex.x_intelligence.daemon"
                    )

                # Ω₁₃: Initialize Memento Specialist & register in SwarmFactory
                try:
                    from cortex.agents.memento import MementoAgent
                    from cortex.swarm.actuators.memento import MementoActuator

                    self._memento_agent = MementoAgent(engine=self)
                    await self._memento_agent.initialize()

                    if self.manager:
                        actuator = MementoActuator(engine=self)
                        self.manager.register_actuator("memento_specialist", actuator)
                        logger.info("Memento specialist registered in SwarmFactory")
                except ImportError:
                    logger.debug("Memento specialist not available — skipping")

        # Enforce 700/600 permissions NOW — db file exists on disk.
        self._enforce_fs_permissions()
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
        self._closed = True
        if self._memory_manager:
            try:
                await asyncio.wait_for(
                    self._memory_manager.wait_for_background(),  # type: ignore
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Memory manager background drain timed out — forcing close")
            memory_l2 = getattr(self._memory_manager, "_l2", None)
            if memory_l2 and hasattr(memory_l2, "close"):
                try:
                    await memory_l2.close()
                except Exception:  # noqa: BLE001
                    logger.debug("Memory L2 shutdown error — ignoring")
            self._memory_manager = None

        signal_bus_conn = getattr(self, "_signal_bus_conn", None)
        if signal_bus_conn is not None:
            try:
                signal_bus_conn.close()
            except Exception:  # noqa: BLE001
                logger.debug("Signal bus connection close error — ignoring")
            self._signal_bus_conn = None
            self._signal_bus = None

        # Ω₁₃: Shutdown Memento Specialist
        if self._memento_agent:
            try:
                await self._memento_agent.shutdown()
            except Exception:  # noqa: BLE001
                logger.debug("Memento agent shutdown error — ignoring")
            self._memento_agent = None
        if self._persistence:
            await self._persistence.stop()

        # Ω₁₃: Shutdown X-Intelligence Daemon
        await self.x_daemon.stop()
        if self._x_daemon_task and not self._x_daemon_task.done():
            self._x_daemon_task.cancel()
            try:
                await self._x_daemon_task
            except asyncio.CancelledError:
                pass
            self._x_daemon_task = None

        if self._conn:
            await self._conn.close()
            self._conn = None
        self._ledger = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
