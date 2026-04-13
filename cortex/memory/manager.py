"""CORTEX v5.3 — Cognitive Memory Orchestrator."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

# Memory OS (RFC-CORTEX-MEMORY-OS)
from cortex.compaction.mem0_pipeline import Mem0Pipeline
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager_support import (
    check_deduplication,
    determine_layer,
    emit_to_bus,
    extract_subject,
    init_dynamic_space,
    init_hologram,
    init_metamemory,
    init_resonance_gate,
    start_bg_workers,
)
from cortex.memory.memory_compression import compress_and_store as _compress_and_store
from cortex.memory.models import MemoryEvent
from cortex.memory.native_arbiter import NativeArbiter
from cortex.memory.schemas import SchemaEngine
from cortex.memory.thalamus import ThalamusGate
from cortex.memory.working import WorkingMemoryL1

try:
    from cortex.memory.hdc import HDCVectorStoreL2
except ImportError:
    HDCVectorStoreL2 = Any  # type: ignore[assignment,misc]

try:
    from cortex.extensions.policy.memory_os import MemoryOS
except ImportError:
    MemoryOS = None  # type: ignore

try:
    from cortex.extensions.security.tenant import get_tenant_id
except ImportError:

    def get_tenant_id() -> str:
        return "default"


try:
    from cortex.extensions.sovereign.endocrine import DigitalEndocrine
except ImportError:
    DigitalEndocrine = None  # type: ignore

from cortex.telemetry.metrics import metrics

try:
    from cortex.extensions.thinking.fusion import ContextFusion
except ImportError:
    ContextFusion = None  # type: ignore

try:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    VectorStoreL2 = None  # type: ignore[assignment,misc]

try:
    from cortex.memory.graph_store import GraphStore
except ImportError:
    GraphStore = None  # type: ignore[misc]

__all__ = ["CortexMemoryManager"]

logger = logging.getLogger("cortex.memory.manager")
compress_and_store = _compress_and_store


def _resolve_manager_tenant(tenant_id: str | None, operation: str) -> str:
    """Resolve tenant context while rejecting blank explicit tenant identifiers."""
    if tenant_id is None:
        return get_tenant_id()

    resolved = tenant_id.strip()
    if not resolved:
        raise ValueError(f"{operation} requires non-blank tenant_id")
    return resolved

class CortexMemoryManager:
    """Orchestrator for the Tripartite Cognitive Memory Architecture.

    Coordinates L1 (Working Memory), L2 (Vector Store), and L3 (Event Ledger)
    into a unified memory pipeline that never blocks the async event loop.

    Args:
        l1: Working memory instance.
        l2: Vector store instance (sqlite-vec backed).
        l3: Event ledger instance (SQLite-backed).
        encoder: Async embedder for L2 vectorization.
        router: Optional LLM router for semantic compression.
    """

    __slots__ = (
        "_encoder",
        "_l1",
        "_l2",
        "_l3",
        "_continual_learning",
        "_continual_training_backend",
        "_hdc",
        "_hdc_encoder",
        "_router",
        "_bg_queue",
        "_bg_workers",
        "_max_bg_tasks",
        "_fusion",
        "_dynamic_space",
        "_hologram",
        "_bus",
        "thalamus",
        "_resonance_gate",
        "_endocrine",
        "_schema_engine",
        "metamemory",
        "_mem0_pipeline",
        "_memory_os",
        "graph_store",
        "_global_writer",
        "_arbiter",
    )

    DEFAULT_MAX_BG_TASKS: int = 100

    def __init__(
        self,
        l1: WorkingMemoryL1,
        l2: VectorStoreL2,  # type: ignore[reportInvalidTypeForm]
        l3: EventLedgerL3,
        encoder: AsyncEncoder,
        continual_learning: Any | None = None,
        continual_training_backend: Any | None = None,
        hdc_l2: Any | None = None,
        hdc_encoder: Any | None = None,
        router: Any | None = None,
        bus: Any | None = None,
        max_bg_tasks: int = DEFAULT_MAX_BG_TASKS,
        global_writer: Any | None = None,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._l3 = l3
        self._encoder = encoder
        self._continual_learning = continual_learning
        self._continual_training_backend = continual_training_backend
        self._hdc = hdc_l2
        self._hdc_encoder = hdc_encoder
        self._router = router
        self._bus = bus
        self._max_bg_tasks = max_bg_tasks
        self._global_writer = global_writer
        self._bg_queue: asyncio.Queue[tuple[list, str, str, str]] = asyncio.Queue(
            maxsize=max_bg_tasks
        )
        self._bg_workers: list[asyncio.Task[Any]] = []
        self.thalamus = ThalamusGate(self)
        self._dynamic_space = init_dynamic_space(self)
        self._hologram = init_hologram(self)

        self._endocrine = DigitalEndocrine() if DigitalEndocrine else None
        self._schema_engine = SchemaEngine()
        self.metamemory = init_metamemory()

        # Memory OS subsystems (RFC-CORTEX-MEMORY-OS / Axiom Ω₁₃)
        self._mem0_pipeline = Mem0Pipeline()
        self._memory_os = MemoryOS() if MemoryOS else None
        if self._memory_os and hasattr(self._memory_os, "start_glial_daemon"):
            self._memory_os.start_glial_daemon()

        # Ontological Memory (Graph RAG) [v6.3 - Cycle 1]
        self.graph_store = GraphStore(db_path="cortex_graph_rag.db") if GraphStore else None

        # ART-v2 Resonance Engine [v6.2]
        self._resonance_gate = init_resonance_gate(self)

        if self._dynamic_space:
            self._dynamic_space.start()
        self._fusion = ContextFusion(judge_provider=router) if ContextFusion else None
        self._arbiter = NativeArbiter()
        start_bg_workers(self)

    async def _should_elevate(self, tenant_id: str, metadata: dict) -> bool:
        """Phase II: Elevation Policy.
        Only high-severity or system-level conflicts cross the bridge.
        """
        if tenant_id == "system":
            return True
        severity = metadata.get("severity", "LOW")
        return severity in ("HIGH", "CRITICAL", "EMERGENCY")

    async def _propagate_conflict(self, event: Any, tenant_id: str, project_id: str):
        """Bridge L3 -> Global Ledger based on policy."""
        if not self._global_writer:
            return

        if await self._should_elevate(tenant_id, event.metadata):
            logger.info("🌉 [BRIDGE] Elevating conflict event %s to global ledger.", event.event_id)
            from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent

            global_event = LedgerEvent.new(
                tool="memory:manager",
                actor="system:epistemic_guard",
                action="CONFLICT_DETECTION",
                target=ActionTarget(identifier=event.metadata["subject_hash"], role="subject"),
                result=ActionResult(ok=False, latency_ms=0, error="EPISTEMIC_CONFLICT"),
                metadata={
                    "memory_event_id": event.event_id,
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "subject_hash": event.metadata["subject_hash"],
                },
            )
            self._global_writer.append(global_event)

    # ─── Primary API ──────────────────────────────────────────────

    async def process_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        token_count: int,
        tenant_id: str | None = None,
        project_id: str = "default_project",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEvent:
        """Process a new interaction through the memory pipeline.

        1. Persist to L3 (immutable ledger)
        2. Push to L1 (working memory)
        3. If overflow → compress and embed to L2 in background
        """
        tenant_id = _resolve_manager_tenant(tenant_id, "process_interaction")
        _meta = metadata or {}
        _meta["tenant_id"] = tenant_id
        _meta["project_id"] = project_id

        event = MemoryEvent(
            role=role,
            content=content,
            session_id=session_id,
            tenant_id=tenant_id,
            token_count=token_count,
            metadata=_meta,
        )

        await self._l3.append_event(event)

        # Ingest into Digital Endocrine system [v6.2]
        if self._endocrine:
            self._endocrine.ingest_context(content, tenant_id=tenant_id, metadata=_meta)

        overflowed = self._l1.add_event(event)

        if overflowed:
            try:
                self._bg_queue.put_nowait((overflowed, session_id, tenant_id, project_id))
            except asyncio.QueueFull:
                logger.critical(
                    "MemoryManager: Background task queue full (max=%d). "
                    "Dropping overflow to protect Event Loop P99 latency.",
                    self._max_bg_tasks,
                )

        if self._continual_learning is not None:
            user_id = _meta.get("user_id", "unknown")
            if not isinstance(user_id, str) or not user_id.strip():
                user_id = "unknown"
            try:
                await asyncio.to_thread(
                    self._continual_learning.on_interaction,
                    tenant_id=tenant_id,
                    user_id=user_id.strip(),
                    text=content,
                    trace_id=event.event_id,
                    metadata={
                        **_meta,
                        "role": role,
                    },
                )
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                logger.warning(
                    "Continual learning sidecar skipped interaction %s: %s", event.event_id, exc
                )

        return event

    async def _check_deduplication(
        self, tenant_id: str, project_id: str, content: str, subject_hash: str
    ) -> dict[str, str | None]:
        """Compatibility wrapper for integrity checks used by tests and patches."""
        return await check_deduplication(self, tenant_id, project_id, content, subject_hash)

    async def store(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        content: str = "",
        fact_type: str = "general",
        metadata: dict[str, Any] | None = None,
        layer: str = "semantic",
        parent_decision_id: str | int | None = None,
        use_bus: bool = False,
        is_diamond: bool = False,
    ) -> str:
        """Directly persist a high-value fact to L2 memory layers.

        Bypasses the L1 working memory buffer. Useful for errors,
        decisions, and formal proof counterexamples.

        Pipeline: Mem0 exergy gate → Thalamus → dedup → encode → resonance → L2
        """
        tenant_id = _resolve_manager_tenant(tenant_id, "store")
        conn = self._l2._get_conn() if hasattr(self._l2, "_get_conn") else None

        # ── Mem0 Exergy Pre-Filter (RFC-CORTEX-MEMORY-OS) ──────────
        exergy = await self._mem0_pipeline.evaluate_exergy(
            {"content": content, "fact_type": fact_type, "metadata": metadata}
        )
        if exergy.score < self._mem0_pipeline.exergy_threshold:
            logger.info(
                "CortexMemoryManager: Fact rejected by Mem0 exergy gate: %s",
                exergy.score,
            )
            return f"filtered:low_exergy:{exergy.score}"

        should_process, action, _ = await self.thalamus.filter(
            content=content,
            project_id=project_id,
            tenant_id=tenant_id,
            fact_type=fact_type,
            parent_decision_id=int(parent_decision_id) if parent_decision_id else None,
            conn=conn,
        )
        if not should_process:
            logger.info("CortexMemoryManager: Fact filtered by Thalamus. Action: %s", action)
            try:
                from cortex.routes.notch_ws import notify_notch_pruning

                await notify_notch_pruning()
            except ImportError:
                logger.debug("notch_ws unavailable (FastAPI not installed), skipping notification")
            return f"filtered:{action}"

        # ── Epistemological Integrity Gate (Ω9) ─────────────
        subject = extract_subject(content, metadata)
        subject_hash = hashlib.sha256(subject.encode()).hexdigest()

        check = await self._check_deduplication(tenant_id, project_id, content, subject_hash)

        if check["status"] == "redundant":
            return f"deduplicated:{check['id']}"

        is_conflict = check["status"] == "conflict"
        if is_conflict:
            logger.error(
                "☣️ [CONFLICTO] Epistemología divergente detectada para hash %s", subject_hash
            )

            # Axiom Ω9: Immutable record of truth collision in L3
            from cortex.memory.models import MemoryEvent

            conflict_event = MemoryEvent(
                role="system",
                content=f"EPISTEMIC_CONFLICT: {content}",
                session_id=project_id,  # Link to project lineage
                tenant_id=tenant_id,
                token_count=0,
                metadata={
                    "type": "epistemic_conflict",
                    "subject_hash": subject_hash,
                    "existing_id": check["id"],
                    "attempted_content": content,
                    **(metadata or {}),
                },
            )
            await self._l3.append_event(conflict_event)
            await self._propagate_conflict(conflict_event, tenant_id, project_id)
            return f"filtered:conflict:{check['id']}"

        _meta = metadata or {}
        if "confidence_score" not in _meta:
            _meta["confidence_score"] = 0.8

        adjusted_layer = determine_layer(project_id, layer)

        if matched_schema := self._schema_engine.match_schema(content):
            content = self._schema_engine.apply_encoding_schema(matched_schema, content)
            _meta.update({"active_schema": matched_schema.name})

        vector = await self._encoder.encode(content)
        fact_id = str(uuid.uuid4())

        candidate = CortexSemanticEngram(
            id=fact_id,
            tenant_id=tenant_id,
            project_id=project_id,
            content=content,
            embedding=vector,
            timestamp=datetime.now(timezone.utc).timestamp(),
            metadata=_meta,
            cognitive_layer=adjusted_layer,  # type: ignore[reportArgumentType]
            parent_decision_id=int(parent_decision_id) if parent_decision_id is not None else None,
            subject_hash=subject_hash,
            is_conflict=is_conflict,
            is_diamond=is_diamond,
        )

        if self._resonance_gate is None:
            raise RuntimeError("Resonance gate unavailable; refusing to persist without validation")

        status, engram = await self._resonance_gate.gate(
            candidate=candidate, precision_mode=(fact_type in ("decision", "rule"))
        )

        if status == "resonance":
            logger.info("CortexMemoryManager: Fact assimilated via resonance with #%s", engram.id)
            return f"deduplicated:{engram.id}"

        if use_bus and self._bus:
            return await emit_to_bus(
                self,
                fact_id, tenant_id, project_id, content, fact_type, adjusted_layer, metadata
            )

        if self._hdc:
            await self._hdc.memorize(engram, fact_type=fact_type)

        # Axiom Ω9: Immutable record of successful assimilation in L3
        from cortex.memory.models import MemoryEvent

        success_event = MemoryEvent(
            role="system",
            content=f"ASSIMILATED: {engram.content}",
            session_id=engram.project_id,
            tenant_id=engram.tenant_id,
            token_count=0,
            metadata={
                "type": "assimilation",
                "fact_id": engram.id,
                "subject_hash": engram.subject_hash,
            },
        )
        await self._l3.append_event(success_event)

        return engram.id

    async def reconcile_experience(self, signal: Any) -> str:
        """Process an experience signal from the bus and commit it to L2."""
        payload = signal.payload
        tenant_id = payload.get("tenant_id")
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("experience signal requires explicit tenant_id")
        return await self.store(
            tenant_id=tenant_id.strip(),
            project_id=payload.get("project_id", "unknown"),
            content=payload.get("content", ""),
            fact_type=payload.get("fact_type", "general"),
            metadata=payload.get("metadata", {}),
            layer=payload.get("layer", "semantic"),
            use_bus=False,
        )

    async def plan_continual_update(
        self,
        *,
        tenant_id: str | None,
        domain: str,
        policy_violation: bool = False,
    ) -> Any | None:
        """Return a continual-learning update plan when the sidecar is enabled."""
        tenant_id = _resolve_manager_tenant(tenant_id, "plan_continual_update")
        if self._continual_learning is None:
            return None
        return await asyncio.to_thread(
            self._continual_learning.plan_micro_update,
            tenant_id=tenant_id,
            domain=domain,
            policy_violation=policy_violation,
        )

    async def continual_learning_status(
        self,
        *,
        tenant_id: str | None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Return a tenant-scoped status view of the continual-learning sidecar."""
        tenant_id = _resolve_manager_tenant(tenant_id, "continual_learning_status")
        if domain is not None and not domain.strip():
            raise ValueError("continual_learning_status requires non-blank domain")
        if self._continual_learning is None:
            return {
                "enabled": False,
                "tenant_id": tenant_id,
                "domain": domain.strip() if domain is not None else None,
                "backend_configured": self._continual_training_backend is not None,
            }
        status = await asyncio.to_thread(
            self._continual_learning.status,
            tenant_id=tenant_id,
            domain=domain,
        )
        status["backend_configured"] = self._continual_training_backend is not None
        return status

    async def execute_continual_update(
        self,
        *,
        tenant_id: str | None,
        domain: str,
        policy_violation: bool = False,
        critical_domains: Iterable[str] = (),
    ) -> Any | None:
        """Execute a continual-learning micro-update when a backend is configured."""
        tenant_id = _resolve_manager_tenant(tenant_id, "execute_continual_update")
        if self._continual_learning is None or self._continual_training_backend is None:
            return None
        return await asyncio.to_thread(
            self._continual_learning.execute_micro_update,
            tenant_id=tenant_id,
            domain=domain,
            backend=self._continual_training_backend,
            policy_violation=policy_violation,
            critical_domains=tuple(critical_domains),
        )

    async def forget_continual_memory(
        self,
        *,
        tenant_id: str | None,
        user_id: str,
        query: str,
    ) -> dict[str, Any] | None:
        """Propagate a selective forgetting request to the continual-learning sidecar."""
        tenant_id = _resolve_manager_tenant(tenant_id, "forget_continual_memory")
        if self._continual_learning is None:
            return None
        return await asyncio.to_thread(
            self._continual_learning.forget,
            tenant_id=tenant_id,
            user_id=user_id,
            query=query,
        )

    async def assemble_context(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        query: str | None = None,
        max_episodes: int = 3,
        fuse_context: bool = False,
        layer: str | None = None,
    ) -> dict[str, Any]:
        """Build an optimized context for LLM injection."""
        tenant_id = _resolve_manager_tenant(tenant_id, "assemble_context")
        working_set = self._l1.get_context(tenant_id=tenant_id)

        _start_recall = time.perf_counter()
        from cortex.memory.memory_retrieval import retrieve_episodic_context

        episodic_facts = await retrieve_episodic_context(
            self, tenant_id, project_id, query, max_episodes, layer=layer
        )
        _recall_duration = time.perf_counter() - _start_recall
        metrics.observe(
            "cortex_recall_latency_seconds",
            _recall_duration,
            {"tenant_id": tenant_id, "project_id": project_id, "layer": layer or "all"},
        )

        context: dict[str, Any] = {
            "working_memory": working_set,
            "episodic_context": episodic_facts,
        }

        if fuse_context and episodic_facts and self._fusion:
            context["episodic_context"] = await self._fusion.fuse_context(
                user_prompt=query or "", retrieved_facts=episodic_facts
            )

        return context

    def get_context_vector(self, tenant_id: str | None = None) -> Any | None:
        """Return the current context as a bundled hypervector (Vector Alpha)."""
        tenant_id = _resolve_manager_tenant(tenant_id, "get_context_vector")
        if not self._hdc_encoder:
            return None
        events = self._l1.get_context(tenant_id=tenant_id)
        if not events:
            return None
        hvs = [self._hdc_encoder.encode_text(e["content"]) for e in events]
        from cortex.memory.hdc.algebra import bundle

        try:
            return hvs[0] if len(hvs) == 1 else bundle(*hvs)
        except (ValueError, TypeError) as e:
            logger.warning("Context vector bundling failed: %s", e)
            return None

    # ─── NREM Consolidation ─────────────────────────────────────────

    async def nrem_consolidation(self, tenant_id: str, project_id: str | None = None) -> dict:
        """Run a full NREM consolidation cycle."""
        from cortex.memory.consolidation import SystemsConsolidator
        from cortex.memory.homeostasis import EntropyPruner, HomeostaticScaler
        from cortex.memory.nrem_cycle import NREMConsolidationCycle

        consolidator = SystemsConsolidator(self._l2) if self._l2 else None
        pruner = EntropyPruner(self._l2) if self._l2 else None
        scaler = HomeostaticScaler(self._l2) if self._l2 else None

        cycle = NREMConsolidationCycle(
            consolidator=consolidator,
            pruner=pruner,
            stdp_engine=getattr(self, "_stdp_engine", None),
            homeostatic_scaler=scaler,
        )
        report = await cycle.run(tenant_id=tenant_id, project_id=project_id)
        import dataclasses

        return dataclasses.asdict(report)

    # ─── Introspection ────────────────────────────────────────────

    @property
    def l1(self) -> WorkingMemoryL1:
        return self._l1

    @property
    def l3(self) -> EventLedgerL3:
        return self._l3

    async def wait_for_background(self, timeout: float = 30.0) -> None:
        """Wait for background tasks to complete with a hard timeout."""
        if self._bg_queue.empty():
            return
        import os

        _testing = os.environ.get("CORTEX_TESTING")
        try:
            await asyncio.wait_for(self._bg_queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("MemoryManager: wait_for_background timed out after %ds", timeout)
            if _testing:
                self._cancel_background_tasks()

    def _cancel_background_tasks(self) -> None:
        """Cancel pending tasks and workers aggressively to prevent event loop leaks."""
        logger.warning("Canceling all background workers and Glial Daemon.")
        glial_daemon_task = getattr(self._memory_os, "_glial_daemon_task", None)
        if glial_daemon_task is not None:
            glial_daemon_task.cancel()

        for worker in self._bg_workers:
            if not worker.done():
                worker.cancel()
        self._bg_workers.clear()

        # Flush the queue
        while not self._bg_queue.empty():
            try:
                self._bg_queue.get_nowait()
                self._bg_queue.task_done()
            except asyncio.QueueEmpty:
                break

    def __repr__(self) -> str:
        return f"CortexMemoryManager(l1={self._l1!r}, bg_queue_size={self._bg_queue.qsize()})"
