# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — Cognitive Memory Orchestrator.

Wires the Tripartite Memory Architecture:
    L1 (Working Memory)  → Token-budgeted sliding window
    L2 (Vector Store)    → sqlite-vec semantic recall
    L3 (Event Ledger)    → SQLite WAL immutable log

Delegates:
    Retrieval  → cortex.memory.memory_retrieval
    Compression → cortex.memory.memory_compression
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.hdc import HDCEncoder, HDCVectorStoreL2
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.memory_compression import compress_and_store, raw_concat
from cortex.memory.memory_retrieval import fact_to_dict, retrieve_episodic_context
from cortex.memory.models import MemoryEvent
from cortex.memory.resonance import AdaptiveResonanceGate
from cortex.memory.schemas import SchemaEngine
from cortex.memory.thalamus import ThalamusGate
from cortex.memory.working import WorkingMemoryL1
from cortex.routes.notch_ws import notify_notch_pruning
from cortex.sovereign.endocrine import DigitalEndocrine
from cortex.telemetry.metrics import metrics
from cortex.thinking.fusion import ContextFusion

try:
    from cortex.memory.semantic_ram import DynamicSemanticSpace
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    VectorStoreL2 = None  # type: ignore[assignment,misc]
    DynamicSemanticSpace = None  # type: ignore[assignment,misc]

__all__ = ["CortexMemoryManager"]

logger = logging.getLogger("cortex.memory.manager")


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
        "_hdc",
        "_hdc_encoder",
        "_router",
        "_background_tasks",
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
    )

    DEFAULT_MAX_BG_TASKS: int = 100

    def __init__(
        self,
        l1: WorkingMemoryL1,
        l2: VectorStoreL2,  # type: ignore[reportInvalidTypeForm]
        l3: EventLedgerL3,
        encoder: AsyncEncoder,
        hdc_l2: HDCVectorStoreL2 | None = None,
        hdc_encoder: HDCEncoder | None = None,
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
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._max_bg_tasks = max_bg_tasks
        self.thalamus = ThalamusGate(self)
        self._dynamic_space = DynamicSemanticSpace(self._l2, manager=self) if self._l2 else None  # type: ignore[reportOptionalCall]

        try:
            from cortex.memory.hologram import HolographicMemory
            self._hologram = HolographicMemory(self._l2) if self._l2 else None
            if self._hologram:
                # We do not await it here, we let it lazy-load or load in background upon first recall
                pass
        except ImportError:
            self._hologram = None

        self._endocrine = DigitalEndocrine()
        self._schema_engine = SchemaEngine()

        from cortex.memory.metamemory import MetamemoryMonitor

        self.metamemory = MetamemoryMonitor()

        # ART-v2 Resonance Engine [v6.2]
        _sensor = None
        try:
            from cortex.songlines.sensor import TopographicSensor

            _sensor = TopographicSensor()
        except ImportError:
            pass

        self._resonance_gate = AdaptiveResonanceGate(
            vector_store=self._l2, songline_sensor=_sensor, endocrine=self._endocrine
        )

        if self._dynamic_space:
            self._dynamic_space.start()
        self._fusion = ContextFusion(judge_provider=router)

    # ─── Primary API ──────────────────────────────────────────────

    async def process_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        token_count: int,
        tenant_id: str = "default_tenant",
        project_id: str = "default_project",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEvent:
        """Process a new interaction through the memory pipeline.

        1. Persist to L3 (immutable ledger)
        2. Push to L1 (working memory)
        3. If overflow → compress and embed to L2 in background
        """
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
        self._endocrine.ingest_context(content, metadata=_meta)

        overflowed = self._l1.add_event(event)

        if overflowed:
            if len(self._background_tasks) >= self._max_bg_tasks:
                logger.warning(
                    "MemoryManager: Background task queue full (%d). Dropping overflow task.",
                    self._max_bg_tasks,
                )
            else:
                task = asyncio.create_task(
                    compress_and_store(self, overflowed, session_id, tenant_id, project_id)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        return event

    def _check_deduplication(self, tenant_id: str, project_id: str, content: str) -> str | None:
        """Return deduplicated ID if fact exists, else None."""
        if not content or not content.strip():
            logger.warning("CortexMemoryManager: Rejected empty fact pipeline.")
            return "empty"

        if self._l2 and hasattr(self._l2, "_get_conn"):
            try:
                conn = self._l2._get_conn()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM facts_meta WHERE tenant_id = ? AND "
                    "project_id = ? AND content = ?",
                    (tenant_id, project_id, content),
                )
                row = cursor.fetchone()
                if row:
                    logger.info("CortexMemoryManager: Fact deduplicated (exact match).")
                    return str(row["id"])
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("CortexMemoryManager: Deduplication check failed: %s", e)
        return None

    def _determine_layer(self, project_id: str, layer: str) -> str:
        """Determine cognitive layer based on project ID semantic rules."""
        _pid_lower = project_id.lower()
        if _pid_lower in ("moskv", "personal", "home", "moskv-1"):
            return "assistant"
        if _pid_lower in ("cortex", "core", "system"):
            return "system"
        return layer if layer else "semantic"

    async def _emit_to_bus(
        self,
        fact_id: str,
        tenant_id: str,
        project_id: str,
        content: str,
        fact_type: str,
        layer: str,
        metadata: dict[str, Any] | None,
    ) -> str:
        """Emit fact record to the experience bus."""
        logger.info("ExperienceBus: Emitting experience:recorded for #%s", fact_id)
        payload = {
            "fact_id": fact_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "content": content,
            "fact_type": fact_type,
            "layer": layer,
            "metadata": metadata or {},
        }
        await asyncio.to_thread(
            self._bus.emit,  # type: ignore[reportOptionalMemberAccess]
            event_type="experience:recorded",
            payload=payload,
            source="memory:manager",
            project=project_id,
        )
        return fact_id

    async def store(
        self,
        tenant_id: str,
        project_id: str,
        content: str,
        fact_type: str = "general",
        metadata: dict[str, Any] | None = None,
        layer: str = "semantic",
        parent_decision_id: str | int | None = None,
        use_bus: bool = False,
    ) -> str:
        """Directly persist a high-value fact to L2 memory layers.

        Bypasses the L1 working memory buffer. Useful for errors,
        decisions, and formal proof counterexamples.
        """
        should_process, action, _ = await self.thalamus.filter(
            content=content, project_id=project_id, tenant_id=tenant_id, fact_type=fact_type
        )
        if not should_process:
            logger.info("CortexMemoryManager: Fact filtered by Thalamus. Action: %s", action)
            await notify_notch_pruning()
            return f"filtered:{action}"

        dedup_id = self._check_deduplication(tenant_id, project_id, content)
        if dedup_id:
            return f"filtered:{dedup_id}" if dedup_id == "empty" else f"deduplicated:{dedup_id}"

        _meta = metadata or {}
        if "confidence_score" not in _meta:
            _meta["confidence_score"] = 0.8

        adjusted_layer = self._determine_layer(project_id, layer)

        # 0. Apply Top-Down Cognitive Schema (Bartlett) before semantic encoding
        matched_schema = self._schema_engine.match_schema(content)
        if matched_schema:
            content = self._schema_engine.apply_encoding_schema(matched_schema, content)
            _meta["active_schema"] = matched_schema.name
            logger.debug(f"Applied Schema '{matched_schema.name}' to Fact Encoding")

        # 1. Encode Content for Resonance Verification
        vector = await self._encoder.encode(content)
        fact_id = str(uuid.uuid4())

        # 2. Build Candidate Engram (CORTEX v6+ Thermodynamic Engine)
        candidate = CortexSemanticEngram(
            id=fact_id,
            tenant_id=tenant_id,
            project_id=project_id,
            content=content,
            embedding=vector,
            timestamp=time.time(),
            metadata=_meta,
            cognitive_layer=adjusted_layer,  # type: ignore[reportArgumentType]
            parent_decision_id=str(parent_decision_id) if parent_decision_id else None,
        )

        # 3. Process through Adaptive Resonance Gate (ART-v2)
        # Replacing simple exact deduplication with semantic resonance.
        # This eliminates semantic overlap, not just string duplication.
        status, engram = await self._resonance_gate.gate(
            candidate=candidate, precision_mode=(fact_type in ("decision", "rule"))
        )

        if status == "resonance":
            # Resonance found! The gate already reinforced the existing engram.
            # We return the existing ID to the caller.
            logger.info("CortexMemoryManager: Fact assimilated via resonance with #%s", engram.id)
            return f"deduplicated:{engram.id}"

        # 4. If we reached here, it's a 'reset' (new engram category)
        # Emit to Experience Bus if required
        if use_bus and self._bus:
            return await self._emit_to_bus(
                fact_id, tenant_id, project_id, content, fact_type, adjusted_layer, metadata
            )

        # 5. Parallel storage (L2 + HDC)
        # Note: L2 store is handled by the gate itself on 'reset' if upsert exists,
        # but we double-check for HDC and persistence.
        if self._hdc:
            await self._hdc.memorize(engram, fact_type=fact_type)

        return engram.id

    async def reconcile_experience(self, signal: Any) -> str:
        """Process an experience signal from the bus and commit it to L2."""
        payload = signal.payload
        return await self.store(
            tenant_id=payload.get("tenant_id", "default"),
            project_id=payload.get("project_id", "unknown"),
            content=payload.get("content", ""),
            fact_type=payload.get("fact_type", "general"),
            metadata=payload.get("metadata", {}),
            layer=payload.get("layer", "semantic"),
            use_bus=False,
        )

    async def assemble_context(
        self,
        tenant_id: str,
        project_id: str,
        query: str | None = None,
        max_episodes: int = 3,
        fuse_context: bool = False,
        layer: str | None = None,
    ) -> dict[str, Any]:
        """Build an optimized context for LLM injection."""
        working_set = self._l1.get_context()

        _start_recall = time.perf_counter()
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

        if fuse_context and episodic_facts:
            context["episodic_context"] = await self._fusion.fuse_context(
                user_prompt=query or "", retrieved_facts=episodic_facts
            )

        return context

    def get_context_vector(self) -> Any | None:
        """Return the current context as a bundled hypervector (Vector Alpha)."""
        if not self._hdc_encoder:
            return None
        events = list(self._l1._buffer)
        if not events:
            return None
        hvs = [self._hdc_encoder.encode_text(e.content) for e in events]
        from cortex.memory.hdc.algebra import bundle

        try:
            return hvs[0] if len(hvs) == 1 else bundle(*hvs)
        except (ValueError, TypeError) as e:
            logger.warning("Context vector bundling failed: %s", e)
            return None

    # ─── NREM Consolidation ─────────────────────────────────────────

    async def nrem_consolidation(
        self,
        tenant_id: str,
        project_id: str | None = None,
    ) -> dict:
        """Run a full NREM consolidation cycle.

        Orchestrates maturation, pruning, STDP decay, and
        homeostatic scaling in a single sweep.
        """
        from cortex.memory.consolidation import SystemsConsolidator
        from cortex.memory.homeostasis import EntropyPruner, HomeostaticScaler
        from cortex.memory.nrem_cycle import NREMConsolidationCycle

        consolidator = SystemsConsolidator(self._l2) if self._l2 else None
        pruner = EntropyPruner(self._l2) if self._l2 else None
        scaler = HomeostaticScaler(self._l2) if self._l2 else None

        stdp = getattr(self, "_stdp_engine", None)

        cycle = NREMConsolidationCycle(
            consolidator=consolidator,
            pruner=pruner,
            stdp_engine=stdp,
            homeostatic_scaler=scaler,
        )
        report = await cycle.run(
            tenant_id=tenant_id,
            project_id=project_id,
        )
        logger.info("NREM consolidation complete: %s", report)
        return {
            "matured": report.matured,
            "deceased": report.deceased,
            "pruned": report.pruned,
            "edges_pruned": report.edges_pruned,
            "engrams_scaled": report.engrams_scaled,
            "scaling_factor": report.scaling_factor,
            "duration_ms": report.duration_ms,
            "errors": report.errors,
        }

    # ─── Introspection ────────────────────────────────────────────

    @property
    def l1(self) -> WorkingMemoryL1:
        return self._l1

    @property
    def l3(self) -> EventLedgerL3:
        return self._l3

    async def wait_for_background(self, timeout: float = 30.0) -> None:
        """Wait for background tasks to complete with a hard timeout."""
        if not self._background_tasks:
            return
        import os

        _testing = os.environ.get("CORTEX_TESTING")
        try:
            async with asyncio.timeout(timeout):
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            logger.error("MemoryManager: wait_for_background timed out after %ds", timeout)
            if _testing:
                self._cancel_background_tasks()

    def _cancel_background_tasks(self) -> None:
        """Cancel pending tasks aggressively to prevent event loop leaks (testing mode)."""
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()
        self._background_tasks.clear()

    # Backward-compat delegates
    _raw_concat = staticmethod(raw_concat)
    _fact_to_dict = staticmethod(fact_to_dict)

    def __repr__(self) -> str:
        return f"CortexMemoryManager(l1={self._l1!r}, bg_tasks={len(self._background_tasks)})"
