# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

# Memory OS (RFC-CORTEX-MEMORY-OS)
from babylon60.compaction.mem0_pipeline import Mem0Pipeline
from babylon60.memory._manager_bg import (
    cancel_background_tasks,
    compression_worker_loop,
)
from babylon60.memory._manager_init import (
    init_dynamic_space,
    init_hologram,
    init_metamemory,
    init_resonance_gate,
)
from babylon60.memory._manager_store import check_deduplication, store_fact
from babylon60.memory.encoder import AsyncEncoder
from babylon60.memory.ledger import EventLedgerL3
from babylon60.memory.models import MemoryEvent
from babylon60.memory.schemas import SchemaEngine
from babylon60.memory.thalamus import ThalamusGate
from babylon60.memory.working import WorkingMemoryL1

try:
    from babylon60.memory.hdc import HDCEncoder, HDCVectorStoreL2
except ImportError:
    HDCEncoder = Any  # type: ignore[assignment,misc]
    HDCVectorStoreL2 = Any  # type: ignore[assignment,misc]

try:
    from babylon60.extensions.policy.memory_os import MemoryOS
except ImportError:
    MemoryOS = None  # type: ignore

try:
    from babylon60.extensions.security.tenant import get_tenant_id
except ImportError:

    def get_tenant_id() -> str:
        return "default"


try:
    from babylon60.extensions.sovereign.endocrine import DigitalEndocrine
except ImportError:
    DigitalEndocrine = None  # type: ignore

from babylon60.telemetry.metrics import metrics

try:
    from babylon60.extensions.thinking.fusion import ContextFusion
except ImportError:
    ContextFusion = None  # type: ignore

try:
    from babylon60.memory.semantic_ram import DynamicSemanticSpace
    from babylon60.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    VectorStoreL2 = None  # type: ignore[assignment,misc]
    DynamicSemanticSpace = None  # type: ignore[assignment,misc]

__all__ = ["CortexMemoryManager"]

logger = logging.getLogger("babylon60.memory.manager")


class CortexMemoryManager:
    """Orchestrator for the Tripartite Cognitive Memory Architecture."""

    __slots__ = (
        "_bg_queue",
        "_bg_workers",
        "_bus",
        "_dynamic_space",
        "_encoder",
        "_endocrine",
        "_fusion",
        "_hdc",
        "_hdc_encoder",
        "_hologram",
        "_l1",
        "_l2",
        "_l3",
        "_max_bg_tasks",
        "_mem0_pipeline",
        "_memory_os",
        "_resonance_gate",
        "_router",
        "_schema_engine",
        "metamemory",
        "thalamus",
    )

    DEFAULT_MAX_BG_TASKS: int = 100

    def __init__(
        self,
        l1: WorkingMemoryL1,
        l2: VectorStoreL2,  # type: ignore[reportInvalidTypeForm]
        l3: EventLedgerL3,
        encoder: AsyncEncoder,
        hdc_l2: Any | None = None,
        hdc_encoder: Any | None = None,
        router: Any | None = None,
        bus: Any | None = None,
        max_bg_tasks: int = DEFAULT_MAX_BG_TASKS,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._l3 = l3
        self._encoder = encoder
        self._hdc = hdc_l2
        self._hdc_encoder = hdc_encoder
        self._router = router
        self._bus = bus
        self._max_bg_tasks = max_bg_tasks
        self._bg_queue: asyncio.Queue[tuple[list, str, str, str]] = asyncio.Queue(
            maxsize=max_bg_tasks
        )
        self._bg_workers: list[asyncio.Task[Any]] = []
        self.thalamus = ThalamusGate(self)
        self._dynamic_space = init_dynamic_space(self._l2, self)
        self._hologram = init_hologram(self._l2)

        self._endocrine = DigitalEndocrine() if DigitalEndocrine else None
        self._schema_engine = SchemaEngine()
        self.metamemory = init_metamemory()

        self._mem0_pipeline = Mem0Pipeline()
        self._memory_os = MemoryOS() if MemoryOS else None
        if self._memory_os and hasattr(self._memory_os, "start_glial_daemon"):
            self._memory_os.start_glial_daemon()

        self._resonance_gate = init_resonance_gate(self._l2, self._endocrine)

        if self._dynamic_space:
            self._dynamic_space.start()
        self._fusion = ContextFusion(judge_provider=router) if ContextFusion else None
        self._start_bg_workers()

    def _start_bg_workers(self) -> None:
        num_workers = min(3, max(1, self._max_bg_tasks // 10))
        for i in range(num_workers):
            task = asyncio.create_task(compression_worker_loop(i, self._bg_queue, self))
            self._bg_workers.append(task)

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
        tenant_id = tenant_id or get_tenant_id()
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

        return event

    async def _check_deduplication(
        self, tenant_id: str, project_id: str, content: str, vector: list[float] | None = None
    ) -> str | None:
        """Forwarder to detached logic."""
        return await check_deduplication(self._l2, tenant_id, project_id, content, vector=vector)

    def _determine_layer(self, project_id: str, layer: str) -> str:
        _pid_lower = project_id.lower()
        if _pid_lower in ("moskv", "personal", "home", "moskv-1"):
            return "assistant"
        if _pid_lower in ("cortex", "core", "system"):
            return "system"
        return layer if layer else "semantic"

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
    ) -> str:
        tenant_id = tenant_id or get_tenant_id()
        return await store_fact(
            self,
            tenant_id,
            project_id,
            content,
            fact_type,
            metadata,
            layer,
            parent_decision_id,
            use_bus,
        )

    async def reconcile_experience(self, signal: Any) -> str:
        payload = signal.payload
        tenant_id = payload.get("tenant_id") or get_tenant_id()
        return await self.store(
            tenant_id=tenant_id,
            project_id=payload.get("project_id", "unknown"),
            content=payload.get("content", ""),
            fact_type=payload.get("fact_type", "general"),
            metadata=payload.get("metadata", {}),
            layer=payload.get("layer", "semantic"),
            use_bus=False,
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
        tenant_id = tenant_id or get_tenant_id()
        working_set = self._l1.get_context(tenant_id=tenant_id)

        _start_recall = time.perf_counter()
        from babylon60.memory.memory_retrieval import retrieve_episodic_context

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
        tenant_id = tenant_id or get_tenant_id()
        if not self._hdc_encoder:
            return None
        events = self._l1.get_context(tenant_id=tenant_id)
        if not events:
            return None
        hvs = [self._hdc_encoder.encode_text(e["content"]) for e in events]
        from babylon60.memory.hdc.algebra import bundle

        try:
            return hvs[0] if len(hvs) == 1 else bundle(*hvs)
        except (ValueError, TypeError) as e:
            logger.warning("Context vector bundling failed: %s", e)
            return None

    # ─── NREM Consolidation ─────────────────────────────────────────

    async def nrem_consolidation(self, tenant_id: str, project_id: str | None = None) -> dict:
        from babylon60.memory.consolidation import SystemsConsolidator
        from babylon60.memory.homeostasis import EntropyPruner, HomeostaticScaler
        from babylon60.memory.nrem_cycle import NREMConsolidationCycle

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
        try:
            if not self._bg_queue.empty():
                try:
                    await asyncio.wait_for(self._bg_queue.join(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.error("MemoryManager: wait_for_background timed out after %ds", timeout)
        finally:
            await self._cancel_background_tasks()

    async def _cancel_background_tasks(self) -> None:
        await cancel_background_tasks(
            self._bg_workers, self._bg_queue, self._memory_os, self._dynamic_space
        )

    def __repr__(self) -> str:
        return f"CortexMemoryManager(l1={self._l1!r}, bg_queue_size={self._bg_queue.qsize()})"
