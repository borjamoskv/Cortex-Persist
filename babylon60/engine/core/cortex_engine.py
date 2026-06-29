# [C5-REAL] Exergy-Maximized
"""CORTEX Engine - Package init.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

from babylon60.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from babylon60.database.mixins.query_mixin import QueryMixin
from babylon60.database.mixins.search_mixin import SearchMixin
from babylon60.database.mixins.sync_mixin import SyncMixin
from babylon60.database.mixins.transaction_mixin import TransactionMixin
from babylon60.engine.core._engine_connection import ConnectionMixin
from babylon60.engine.core._engine_delegates import DelegatesMixin
from babylon60.engine.core.durability import PersistenceSupervisor
from babylon60.engine.core.memory_mixin import MemoryMixin
from babylon60.engine.core.store_mixin import StoreMixin
from babylon60.engine.mixins.components import ComponentsMixin
from babylon60.engine.mixins.optimization import OptimizationMixin
from babylon60.swarm.agent_mixin import AgentMixin

if TYPE_CHECKING:
    from babylon60.consensus.manager import ConsensusManager
    from babylon60.embeddings import LocalEmbedder
    from babylon60.embeddings.manager import EmbeddingManager
    from babylon60.engine.flow.lock import SovereignLock
    from babylon60.facts.manager import FactManager
    from babylon60.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from babylon60.mac_maestro.executor import MaestroExecutor
    from babylon60.swarm.auth import ByzantineAuthLayer
    from babylon60.swarm.trust_registry import TrustRegistry
try:
    from babylon60.extensions.health.health_mixin import (
        HealthMixin,  # pyright: ignore[reportAssignmentType]
    )
except ImportError:

    class HealthMixin:
        async def health_check(self, *args, **kwargs):
            """Document health_check"""
            return {"status": "unhealthy", "reason": "No Health extension"}

        async def health_report(self, *args, **kwargs):
            """Document health_report"""
            return {"status": "unhealthy", "reason": "No Health extension"}


logger = logging.getLogger("cortex.engine.guards")
MAX_TAGS_PER_FACT = 20


class CortexEngine(
    ConnectionMixin,
    DelegatesMixin,
    SearchMixin,
    StoreMixin,
    QueryMixin,
    MemoryMixin,
    TransactionMixin,
    OptimizationMixin,
    HealthMixin,
    SyncMixin,
    AgentMixin,
    ComponentsMixin,
):
    """The Sovereign Ledger for AI Agents (Composite Orchestrator)."""

    def __init__(
        self, db_path: str | Path | Any = DEFAULT_DB_PATH, auto_embed: bool = True, pool: Any = None
    ):
        self._skills_verified: set[str] = set()
        if not isinstance(db_path, str | Path) and (not hasattr(db_path, "acquire")):
            raise TypeError(
                f"CortexEngine: db_path must be str, Path, or a pool object (with .acquire()), got {type(db_path).__name__!r}. Did you swap pool and db_path arguments?"
            )
        if hasattr(db_path, "acquire") and (not isinstance(db_path, str | Path)):
            self._pool = db_path
            self._db_path = Path(str(auto_embed)).expanduser()
            self._auto_embed = True
        else:
            self._db_path = Path(str(db_path)).expanduser()
            self._auto_embed = auto_embed
            self._pool = pool
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection | None = None
        self._thread_init_lock = threading.Lock()
        self._vec_available = False
        self._schema_ready = False
        self._ledger = None
        self._embedder: LocalEmbedder | None = None
        self._memory_manager = None
        self._memory_l1 = None
        self._memory_l3 = None
        self._memory_ready = False
        self._persistence = PersistenceSupervisor(self)
        self._system_state = "ACTIVE"
        self._facts: FactManager | None = None
        self._embeddings: EmbeddingManager | None = None
        self._consensus: ConsensusManager | None = None
        self._lock_sovereign: SovereignLock | None = None
        self._ledger_store: LedgerStore | None = None
        self._enrichment_queue: EnrichmentQueue | None = None
        self._ledger_writer: LedgerWriter | None = None
        self._mac_maestro: MaestroExecutor | None = None
        self._auth: ByzantineAuthLayer | None = None
        self._trust_registry: TrustRegistry | None = None
        self._guard_pipeline = self._register_default_guards()
        self._buffer_task = None
        self._post_commit_tasks: set[asyncio.Task[Any]] = set()
        self._pending_graph_jobs: dict[int, list[dict[str, Any]]] = {}

    @property
    def system_state(self) -> str:
        """Get the current system state."""
        return self._system_state

    def set_system_state(self, state: str) -> None:
        """Lock or unlock the sovereign engine (e.g., from EpistemicCircuitBreaker)"""
        self._system_state = state
        logger.warning("🛡️ [SOVEREIGN-STATE] CORTEX Engine state changed to: %s", state)

    async def report_anomaly(self, epicenter_node: str, dependency_graph: dict[str, Any], execution_time: float = 1.0) -> bool:
        """
        Ingest an anomaly report and automatically trigger UltraThink P0 if thermodynamic conditions are met.
        (Blast Radius >= 3)
        """
        try:
            from babylon60.engine.core.ultrathink_physics import UltrathinkPhysicsEngine
            
            radius = UltrathinkPhysicsEngine.measure_blast_radius(dependency_graph, epicenter_node)
            
            # Default exergy values for anomaly detection (High stochasticity)
            stochastic_entropy = 0.9
            deterministic_output = 1.0
            
            authorized, reason, formation = UltrathinkPhysicsEngine.authorize_ultrathink(
                stochastic_entropy, deterministic_output, execution_time, radius, epicenter_node
            )
            
            if authorized and formation:
                logger.critical("🚨 [ULTRATHINK P0] Anomaly threshold breached. Triggering automatic P0 protocol.")
                logger.critical("Reason: %s", reason)
                self.set_system_state("APEX_STATE")
                
                # Emit system-wide critical alert to the Ledger
                try:
                    from babylon60.agents.primitives.dispatcher import apex_dispatcher
                    apex_dispatcher.execute(
                        "OP_GIT_SENTINEL",
                        commit_msg=f"CORTEX-ULTRATHINK: P0 Singularity Auto-Triggered at {epicenter_node} ({formation.value})",
                        force=False,
                    )
                except ImportError:
                    pass
                return True
            else:
                logger.debug("Anomaly reported at %s, but UltraThink not authorized: %s", epicenter_node, reason)
                return False
        except Exception as e:
            logger.error("Failed to process anomaly report: %s", e)
            return False

    def _synthesize_skill(self, skill_name: str) -> None:
        """JIT skill synthesis (Axiom Ω₄)."""
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

    @staticmethod
    def _audit_log(
        action: str, fact_type: str = "", project: str = "", tenant_id: str = "default"
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

    def _get_embedder(self) -> Any:
        """Protocol requirement for SearchMixin."""
        if self._embedder is None:
            try:
                from babylon60.embeddings import LocalEmbedder

                self._embedder = LocalEmbedder()
            except ImportError:
                return None
        return self._embedder

    async def start(self) -> None:
        """Ignite the sovereign engine and its optimization layers."""
        await self.start_optimizer()
        await self._persistence.start()
        
        # [Mutation 3: Crypto/Dimension Agility]
        try:
            if self.embeddings:
                await self.embeddings.check_and_reindex()
        except Exception as e:
            logger.warning("Re-indexing check skipped/failed: %s", e)
            
        logger.info("🚀 [CORTEX] Sovereign Engine ignited (Ω₀-Ω₆).")

    async def close(self):
        """Shutdown the engine, optimizer, and database connections."""
        self._closing = True
        await self.stop_optimizer()
        await self._drain_tasks()

        self._memory_l1 = None
        self._memory_l3 = None
        self._memory_ready = False
        if self._persistence:
            await self._persistence.stop()

        await self._close_connections()

        self._mac_maestro = None
        self._ledger_writer = None
        self._enrichment_queue = None
        self._ledger_store = None
        self._ledger = None

    async def _drain_tasks(self):
        if self._post_commit_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._post_commit_tasks, return_exceptions=True), timeout=5.0
                )
            except (asyncio.TimeoutError, asyncio.CancelledError, RuntimeError, ValueError):
                logger.debug("Post-commit task drain timed out - forcing close")
            self._post_commit_tasks.clear()
        if self._memory_manager:
            try:
                await asyncio.wait_for(self._memory_manager.wait_for_background(), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, RuntimeError, ValueError):
                logger.debug("Memory manager background drain timed out - forcing close")
            self._memory_manager = None

    async def _close_connections(self):
        if hasattr(self, "_sync_conns"):
            for conn in self._sync_conns:
                try:
                    conn.close()
                except (ValueError, TypeError, KeyError, OSError, RuntimeError):
                    pass
            self._sync_conns.clear()

        if not hasattr(self, "_conns_by_loop"):
            return
        conns = list(self._conns_by_loop.values())
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        for conn in conns:
            conn_loop = getattr(conn, "_cortex_loop", current_loop)
            if conn_loop is None or conn_loop.is_closed():
                self._stop_dead_connection(conn)
                continue
            if conn_loop is current_loop:
                try:
                    await conn.close()
                except (RuntimeError, ValueError, AttributeError):
                    pass
            else:
                try:
                    asyncio.run_coroutine_threadsafe(conn.close(), conn_loop)
                except (RuntimeError, ValueError, AttributeError):
                    pass
        self._conns_by_loop.clear()

    def _stop_dead_connection(self, conn):
        if hasattr(conn, "_tx"):
            try:
                from aiosqlite.core import _STOP_RUNNING_SENTINEL

                def close_and_stop(c=conn):
                    if getattr(c, "_connection", None) is not None:
                        try:
                            c._connection.close()
                        except (RuntimeError, ValueError, AttributeError):
                            pass
                        c._connection = None
                    return _STOP_RUNNING_SENTINEL

                conn._tx.put_nowait((None, close_and_stop))
            except (RuntimeError, ValueError, AttributeError):
                if hasattr(conn, "stop"):
                    conn.stop()
        elif hasattr(conn, "stop"):
            conn.stop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


AsyncCortexEngine = CortexEngine
