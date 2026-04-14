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

from cortex.config import DEFAULT_DB_PATH
from cortex.database.core import load_sqlite_vec_async

# Lazy imports for runtime managers
if TYPE_CHECKING:
    from cortex.consensus.manager import ConsensusManager
    from cortex.embeddings import LocalEmbedder
    from cortex.embeddings.manager import EmbeddingManager
    from cortex.engine.auth import ByzantineAuthLayer
    from cortex.engine.lock import SovereignLock
    from cortex.engine.trust_registry import TrustRegistry
    from cortex.facts.manager import FactManager
    from cortex.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from cortex.mac_maestro.executor import MaestroExecutor
from cortex.database.schema import get_init_meta
from cortex.engine.agent_mixin import AgentMixin
from cortex.engine.durability import PersistenceSupervisor
from cortex.engine.legacy_mixin import LegacyMixin
from cortex.engine.memory_mixin import MemoryMixin
from cortex.engine.mixins.base import FACT_COLUMNS, FACT_JOIN
from cortex.engine.mixins.optimization import OptimizationMixin
from cortex.engine.models import row_to_fact  # noqa: F401 — re-exported
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.search_mixin import SearchMixin
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.sync_mixin import SyncMixin
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

logger = logging.getLogger("cortex.engine.guards")
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
    SyncMixin,
    AgentMixin,
    LegacyMixin,
):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""
    def __init__(
        self,
        db_path: str | Path | Any = DEFAULT_DB_PATH,
        auto_embed: bool = True,
        pool: Any = None,
    ):
        # Axiom Ω₁₆: Sortu-Native JIT Synthesis
        # We defer Mixin.__init__ calls to _synthesize_skill for 10k scale.
        self._skills_verified: set[str] = set()
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
        self._conn: aiosqlite.Connection | None = None
        self._vec_available = False
        self._conn_lock = asyncio.Lock()
        self._schema_lock = asyncio.Lock()
        self._schema_ready = False
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)
        self._embedder: LocalEmbedder | None = None
        self._memory_manager = None  # Frontera 2: Tripartite Memory (lazy init)
        self._memory_l1 = None
        self._memory_l3 = None
        self._memory_ready = False
        self._persistence = PersistenceSupervisor(self)
        self._system_state = "ACTIVE"
        # Managers are synthesized JIT via properties (Axiom Ω₄)
        self._facts: FactManager | None = None  # noqa: F821
        self._embeddings: EmbeddingManager | None = None
        self._consensus: ConsensusManager | None = None
        self._lock_sovereign: SovereignLock | None = None
        self._ledger_store: LedgerStore | None = None
        self._enrichment_queue: EnrichmentQueue | None = None
        self._ledger_writer: LedgerWriter | None = None
        self._mac_maestro: MaestroExecutor | None = None
        self._auth: ByzantineAuthLayer | None = None  # noqa: F821
        self._trust_registry: TrustRegistry | None = None
        # Decoupled guard pipeline (Ω₃: minimal coupling)
        self._guard_pipeline = self._register_default_guards()
        self._buffer_task = None
        self._post_commit_tasks: set[asyncio.Task[Any]] = set()
        self._pending_graph_jobs: dict[int, list[dict[str, Any]]] = {}
    # ─── System State ─────────────────────────────────────────────────────────
    @property
    def system_state(self) -> str:
        return self._system_state
    def set_system_state(self, state: str) -> None:
        """Lock or unlock the sovereign engine (e.g., from EpistemicCircuitBreaker)"""
        self._system_state = state
        logger.warning("🛡️ [SOVEREIGN-STATE] CORTEX Engine state changed to: %s", state)
    def _synthesize_skill(self, skill_name: str) -> None:
        """JIT skill synthesis (Axiom Ω₄).
        Initializes mixin state only when first bit of exergy is required.
        """
        if skill_name in self._skills_verified:
            return
        SKILL_MAP = {
            "search": SearchMixin,
            "store": StoreMixin,
            "query": QueryMixin,
            "memory": MemoryMixin,
            "tx": TransactionMixin,
            "optimization": OptimizationMixin,
            "health": HealthMixin,
        }
        if skill_name in SKILL_MAP:
            SKILL_MAP[skill_name].__init__(self)
            self._skills_verified.add(skill_name)
            logger.debug("🛡️ [SORTU-JIT] Skill '%s' synthesized.", skill_name)
    @property
    def facts(self) -> FactManager:  # noqa: F821
        if self._facts is None:
            from cortex.facts.manager import FactManager
            self._facts = FactManager(self)  # type: ignore
        return self._facts
    @facts.setter
    def facts(self, value: FactManager) -> None:  # noqa: F821
        self._facts = value
    @property
    def embeddings(self) -> EmbeddingManager:
        if self._embeddings is None:
            from cortex.embeddings.manager import EmbeddingManager
            self._embeddings = EmbeddingManager(self)
        return self._embeddings
    @embeddings.setter
    def embeddings(self, value: EmbeddingManager) -> None:
        self._embeddings = value
    @property
    def consensus(self) -> ConsensusManager:
        if self._consensus is None:
            from cortex.consensus.manager import ConsensusManager
            self._consensus = ConsensusManager(self)
        return self._consensus
    @consensus.setter
    def consensus(self, value: ConsensusManager) -> None:
        self._consensus = value
    @property
    def lock_sovereign(self) -> SovereignLock:
        if self._lock_sovereign is None:
            from cortex.engine.lock import SovereignLock
            self._lock_sovereign = SovereignLock(self)
        return self._lock_sovereign
    @lock_sovereign.setter
    def lock_sovereign(self, value: SovereignLock) -> None:
        self._lock_sovereign = value
    @property
    def auth(self) -> ByzantineAuthLayer:  # noqa: F821
        if self._auth is None:
            from cortex.engine.auth import ByzantineAuthLayer
            self._auth = ByzantineAuthLayer()
        return self._auth
    @auth.setter
    def auth(self, value: ByzantineAuthLayer) -> None:  # noqa: F821
        self._auth = value
    @property
    def ledger_store(self) -> LedgerStore:
        if self._ledger_store is None:
            from cortex.ledger import LedgerStore
            self._ledger_store = LedgerStore(self._db_path)
        return self._ledger_store
    @ledger_store.setter
    def ledger_store(self, value: LedgerStore) -> None:
        self._ledger_store = value
    @property
    def enrichment_queue(self) -> EnrichmentQueue:
        if self._enrichment_queue is None:
            from cortex.ledger import EnrichmentQueue
            self._enrichment_queue = EnrichmentQueue(self.ledger_store)
        return self._enrichment_queue
    @enrichment_queue.setter
    def enrichment_queue(self, value: EnrichmentQueue) -> None:
        self._enrichment_queue = value
    @property
    def ledger_writer(self) -> LedgerWriter:
        if self._ledger_writer is None:
            from cortex.ledger import LedgerWriter
            self._ledger_writer = LedgerWriter(self.ledger_store, self.enrichment_queue)
        return self._ledger_writer
    @ledger_writer.setter
    def ledger_writer(self, value: LedgerWriter) -> None:
        self._ledger_writer = value
    @property
    def mac_maestro(self) -> MaestroExecutor:
        if self._mac_maestro is None:
            from cortex.mac_maestro.executor import MaestroExecutor
            self._mac_maestro = MaestroExecutor(self.ledger_writer)
        return self._mac_maestro
    @mac_maestro.setter
    def mac_maestro(self, value: MaestroExecutor) -> None:
        self._mac_maestro = value
    # ─── Guard Pipeline Registration ──────────────────────────────
    def _register_default_guards(self):
        """Build the GuardPipeline with all available guard adapters.
        Each adapter is imported defensively — if the underlying module
        is not installed, the adapter is skipped. Runtime failures during
        guard construction are treated as fatal because the write path must
        fail closed.
        """
        from cortex.engine.guard_pipeline import GuardPipeline
        pipeline = GuardPipeline()
        db_path = str(self._db_path)
        # Pre-store guards (AX-II Hooks 1-3)
        try:
            from cortex.engine.guard_adapters import HealthGuardAdapter
            pipeline.add_guard(HealthGuardAdapter(db_path))
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: HealthGuardAdapter failed: {e}") from e
            logger.debug("HealthGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: HealthGuardAdapter failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import ContradictionGuardAdapter
            pipeline.add_guard(ContradictionGuardAdapter(db_path))
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ContradictionGuardAdapter failed: {e}") from e
            logger.debug("ContradictionGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: ContradictionGuardAdapter failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import VerifierGuardAdapter
            pipeline.add_guard(VerifierGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: VerifierGuardAdapter failed: {e}") from e
            logger.debug("VerifierGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: VerifierGuardAdapter failed: {e}") from e
        # ZK-Swarm Cryptographic Guard (RFC-003 Phase 1)
        try:
            from cortex.engine.guard_adapters import ZKGuardAdapter
            pipeline.add_guard(ZKGuardAdapter())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: ZKGuardAdapter failed: {e}") from e
            logger.debug("ZKGuardAdapter unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: ZKGuardAdapter failed: {e}") from e
        # Post-store hooks (AX-II Hook 4 + signals + epistemic)
        try:
            from cortex.engine.guard_adapters import LedgerCheckpointHook
            pipeline.add_post_hook(LedgerCheckpointHook(self))
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: LedgerCheckpointHook failed: {e}") from e
            logger.debug("LedgerCheckpointHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: LedgerCheckpointHook failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import SignalEmitHook
            pipeline.add_post_hook(SignalEmitHook())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: SignalEmitHook failed: {e}") from e
            logger.debug("SignalEmitHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: SignalEmitHook failed: {e}") from e
        try:
            from cortex.engine.guard_adapters import EpistemicBreakerHook
            pipeline.add_post_hook(EpistemicBreakerHook())
        except ImportError as e:
            if os.environ.get("CORTEX_STRICT_GUARDS") == "1":
                raise RuntimeError(f"FAIL-CLOSED: EpistemicBreakerHook failed: {e}") from e
            logger.debug("EpistemicBreakerHook unavailable: %s", e)
        except Exception as e:
            raise RuntimeError(f"FAIL-CLOSED: EpistemicBreakerHook failed: {e}") from e
        logger.debug(
            "GuardPipeline: %d guards, %d hooks registered",
            pipeline.guard_count,
            pipeline.hook_count,
        )
        return pipeline
    # ─── JIT Entry Points (Axiom Ω₄) ──────────────────────────────
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
            from cortex.embeddings import LocalEmbedder
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
            self._vec_available = await load_sqlite_vec_async(self._conn)
            await self._ensure_schema_ready(self._conn)
            # Ensure memory subsystem is initialized (L1/L2/L3)
            # This is critical for Active Forgetting (Thalamus Gate)
            if not self._memory_ready:
                await self._init_memory_subsystem(self._db_path, self._conn)
            return self._conn
    async def _ensure_schema_ready(self, conn: aiosqlite.Connection) -> None:
        """Bootstrap the base schema once per engine instance."""
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            await run_migrations_async(conn)
            for k, v in get_init_meta():
                await conn.execute(
                    "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                    (k, v),
                )
            await conn.commit()
            if self._ledger is None:
                from cortex.ledger import ImmutableLedger
                self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
            self._schema_ready = True
    async def _get_or_create_ledger(self):
        """Return the transaction ledger, initializing it on demand."""
        conn = await self._get_or_create_conn()
        await self._ensure_schema_ready(conn)
        if self._ledger is None:
            from cortex.ledger import ImmutableLedger
            self._ledger = ImmutableLedger(conn)  # type: ignore[reportArgumentType]
        return self._ledger
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
    # ─── Backward Compatibility Aliases & Delegation ──────────────
    async def store(self, *args, **kwargs):
        self._synthesize_skill("store")
        self._audit_log(
            "store",
            fact_type=kwargs.get("fact_type", ""),
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await self.facts.store(*args, **kwargs)
    async def store_many(self, *args, **kwargs):
        self._synthesize_skill("store")
        return await super().store_many(*args, **kwargs)
    async def recall(self, *args, **kwargs):
        self._synthesize_skill("search")
        self._audit_log(
            "recall",
            project=kwargs.get("project", args[0] if args else ""),
        )
        return await super().recall(*args, **kwargs)
    async def search(self, *args, **kwargs):
        self._synthesize_skill("search")
        return await super().search(*args, **kwargs)
    async def query(self, *args, **kwargs):
        self._synthesize_skill("query")
        return await super().query(*args, **kwargs)
    async def write_optimized(self, *args, **kwargs):
        self._synthesize_skill("optimization")
        return await super().write_optimized(*args, **kwargs)
    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        self._synthesize_skill("query")
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
    async def get_votes(self, *args, **kwargs):
        return await self.consensus.get_votes(*args, **kwargs)
    async def verify_vote_ledger(self, *args, **kwargs):
        return await self.consensus.verify_vote_ledger(*args, **kwargs)
    async def propagate_taint(self, fact_id: int, tenant_id: str = "default"):
        """Propagate causal taint through the tenant-scoped causality graph."""
        from cortex.engine.causality import AsyncCausalGraph
        tenant_id = self._resolve_tenant(tenant_id)
        async with self.session() as conn:
            graph = AsyncCausalGraph(conn)
            await graph.ensure_table()
            return await graph.propagate_taint(fact_id, tenant_id=tenant_id)
    def get_trust_registry(self):
        """Return the in-memory trust registry used by trust endpoints."""
        if self._trust_registry is None:
            from cortex.engine.trust_registry import TrustRegistry
            self._trust_registry = TrustRegistry()
        return self._trust_registry
    async def create_checkpoint(self) -> str | None:
        """Create a transaction-ledger Merkle checkpoint."""
        ledger = await self._get_or_create_ledger()
        return await ledger.create_checkpoint_async()
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
    async def immortality_index(self, project: str | None = None) -> dict:
        """Immortality Index (ι) — cognitive crystallization metric."""
        from cortex.extensions.shannon.immortality import ImmortalityIndex
        return await ImmortalityIndex.compute(self, project)
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
        conn = await self._get_or_create_conn()
        await self._ensure_schema_ready(conn)
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
        if self._post_commit_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._post_commit_tasks, return_exceptions=True),
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Post-commit task drain timed out — forcing close")
            self._post_commit_tasks.clear()
        if self._memory_manager:
            try:
                await asyncio.wait_for(
                    self._memory_manager.wait_for_background(),  # type: ignore
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Memory manager background drain timed out — forcing close")
            self._memory_manager = None
        self._memory_l1 = None
        self._memory_l3 = None
        self._memory_ready = False
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
