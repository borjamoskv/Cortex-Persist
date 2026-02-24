# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — Cognitive Memory Orchestrator.

Wires the Tripartite Memory Architecture:
    L1 (Working Memory)  → Token-budgeted sliding window
    L2 (Vector Store)    → Qdrant-backed semantic recall
    L3 (Event Ledger)    → SQLite WAL immutable log

Flow: interaction → L3 (persist) → L1 (buffer) → overflow → L2 (compress+embed)

Background compression uses `asyncio.create_task` to avoid blocking
the primary inference path. When a CortexLLMRouter is configured,
overflow events are semantically summarized before embedding.
Without a router, compression degrades to raw concatenation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.hdc import HDCEncoder, HDCVectorStoreL2
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import CortexFactModel, MemoryEntry, MemoryEvent
from cortex.memory.working import WorkingMemoryL1
from cortex.thinking.context_fusion import ContextFusion

try:
    from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

    VectorStoreL2 = SovereignVectorStoreL2
except ImportError:
    VectorStoreL2 = None  # type: ignore[assignment,misc]

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
    )

    DEFAULT_MAX_BG_TASKS: int = 100

    def __init__(
        self,
        l1: WorkingMemoryL1,
        l2: VectorStoreL2,
        l3: EventLedgerL3,
        encoder: AsyncEncoder,
        hdc_l2: HDCVectorStoreL2 | None = None,
        hdc_encoder: HDCEncoder | None = None,
        router: Any | None = None,
        max_bg_tasks: int = DEFAULT_MAX_BG_TASKS,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._l3 = l3
        self._encoder = encoder
        self._hdc = hdc_l2
        self._hdc_encoder = hdc_encoder
        self._router = router
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._max_bg_tasks = max_bg_tasks

        # Semantic Fusion Layer
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

        Args:
            role: Interaction role (user/assistant/system/tool).
            content: Raw content.
            session_id: Session identifier.
            token_count: Token count estimate.
            tenant_id: Zero-Trust boundary isolation ID.
            project_id: Zero-Trust boundary project ID.
            metadata: Optional structured metadata.

        Returns:
            The created MemoryEvent.
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

        # 1. Immutable persistence (WAL — ultra-fast)
        await self._l3.append_event(event)

        # 2. Working memory update
        overflowed = self._l1.add_event(event)

        # 3. Background compression (non-blocking, bounded queue)
        if overflowed:
            if len(self._background_tasks) >= self._max_bg_tasks:
                logger.warning(
                    "MemoryManager: Background task queue full (%d). Dropping overflow task.",
                    self._max_bg_tasks,
                )
            else:
                task = asyncio.create_task(
                    self._compress_and_store(overflowed, session_id, tenant_id, project_id)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

    async def store(
        self,
        tenant_id: str,
        project_id: str,
        content: str,
        fact_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Directly persist a high-value fact to L2 memory layers.

        Bypasses the L1 working memory buffer. Useful for errors,
        decisions, and formal proof counterexamples.
        """
        fact_id = uuid.uuid4().hex
        vector = await self._encoder.encode(content)
        fact = CortexFactModel(
            id=fact_id,
            tenant_id=tenant_id,
            project_id=project_id,
            content=content,
            embedding=vector,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        
        # Store in Sovereign L2
        if self._l2:
            await self._l2.memorize(fact)
            
        # Store in HDC L2 (Vector Alpha/Gamma)
        if self._hdc:
            await self._hdc.memorize(fact, fact_type=fact_type)
            
        return fact_id

    async def assemble_context(
        self,
        tenant_id: str,
        project_id: str,
        query: str | None = None,
        max_episodes: int = 3,
        fuse_context: bool = False,
    ) -> dict[str, Any]:
        """Build an optimized context for LLM injection."""
        # 1. Working Memory (L1)
        working_set = self._l1.get_context()

        # 2. Episodic Retrieval (L2 + HDC)
        episodic_facts = await self._retrieve_episodic_context(
            tenant_id, project_id, query, max_episodes
        )

        # 3. Context Construction
        context: dict[str, Any] = {
            "working_memory": working_set,
            "episodic_context": episodic_facts,
        }

        # 4. Optional Semantic Fusion
        if fuse_context and episodic_facts:
            context["episodic_context"] = await self._fusion.fuse_context(
                user_prompt=query or "",
                retrieved_facts=episodic_facts
            )

        return context

    async def _retrieve_episodic_context(
        self, tenant_id: str, project_id: str, query: str | None, max_episodes: int
    ) -> list[dict[str, Any]]:
        """Retrieve and fuse facts from all available L2 layers."""
        if not query:
            return []

        dense_results: list[CortexFactModel] = []
        hdc_results: list[CortexFactModel] = []

        # HDC (Vector Alpha + Vector Gamma Inhibition)
        if self._hdc:
            hdc_results = await self._fetch_hdc_results(tenant_id, project_id, query, max_episodes)

        # Dense (Legacy Fallback)
        if not hdc_results and self._l2:
            dense_results = await self._fetch_dense_results(tenant_id, project_id, query, max_episodes)

        # Fusion
        if hdc_results and dense_results:
            return self._apply_rrf(dense_results, hdc_results, limit=max_episodes)
        elif hdc_results:
            return [self._fact_to_dict(f) for f in hdc_results[:max_episodes]]
        else:
            return [self._fact_to_dict(f) for f in dense_results[:max_episodes]]

    async def _fetch_hdc_results(
        self, tenant_id: str, project_id: str, query: str, max_episodes: int
    ) -> list[CortexFactModel]:
        try:
            toxic_ids = await self._hdc.get_toxic_ids(tenant_id=tenant_id, project_id=project_id)
            return await self._hdc.recall_secure(
                tenant_id=tenant_id,
                project_id=project_id,
                query=query,
                limit=max_episodes * 2,
                inhibit_ids=toxic_ids,
            )
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("HDC recall failed: %s", e)
            return []

    async def _fetch_dense_results(
        self, tenant_id: str, project_id: str, query: str, max_episodes: int
    ) -> list[CortexFactModel]:
        try:
            if hasattr(self._l2, "recall_secure"):
                return await self._l2.recall_secure(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    query=query,
                    limit=max_episodes,
                )
            return await self._l2.recall(
                query=query, limit=max_episodes, tenant_id=tenant_id
            )
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Dense L2 recall failed: %s", e)
            return []


    def _apply_rrf(
        self,
        dense: list[CortexFactModel],
        hdc: list[CortexFactModel],
        limit: int = 3,
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """Apply Reciprocal Rank Fusion to merge dense and HDC results."""
        scores: dict[str, float] = {}
        facts: dict[str, CortexFactModel] = {}

        for rank, fact in enumerate(dense):
            scores[fact.id] = scores.get(fact.id, 0.0) + 1.0 / (k + rank + 1)
            facts[fact.id] = fact

        for rank, fact in enumerate(hdc):
            scores[fact.id] = scores.get(fact.id, 0.0) + 1.0 / (k + rank + 1)
            facts[fact.id] = fact

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [self._fact_to_dict(facts[fid], rrf_score=scores[fid]) for fid in sorted_ids[:limit]]

    @staticmethod
    def _fact_to_dict(fact: CortexFactModel, rrf_score: float | None = None) -> dict[str, Any]:
        """Convert a fact model to a context-ready dict."""
        return {
            "id": fact.id,
            "content": fact.content,
            "timestamp": fact.timestamp,
            "score": rrf_score if rrf_score is not None else getattr(fact, "_recall_score", 0.0),
            "metadata": fact.metadata,
        }

    # ─── Background Compression ───────────────────────────────────

    async def _compress_and_store(
        self,
        events: list[MemoryEvent],
        session_id: str,
        tenant_id: str,
        project_id: str,
    ) -> None:
        """Compress overflowed events and store in L2 (v6 sovereign or legacy)."""
        try:
            summary = await self._summarize_events(events)

            # Check if we are using the Sovereign (v6) Vector Store
            is_sovereign = self._l2.__class__.__name__ == "SovereignVectorStoreL2"

            if is_sovereign:
                # v6 Strategy: CortexFactModel (SQLite-Vec)
                vector = await self._encoder.encode(summary)
                fact = CortexFactModel(
                    id=uuid.uuid4().hex,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    content=summary,
                    embedding=vector,
                    timestamp=time.time(),
                    metadata={
                        "session_id": session_id,
                        "event_count": len(events),
                        "linked_events": [e.event_id for e in events],
                        "compression": "llm" if self._router else "raw",
                    },
                )
                await self._l2.memorize(fact)

                # Vector Alpha: Dual-write to HDC if enabled
                if self._hdc:
                    await self._hdc.memorize(fact)
            else:
                # v5 Strategy: Legacy MemoryEntry (Qdrant)
                entry = MemoryEntry(
                    content=summary,
                    project=project_id,
                    source="episodic",
                    metadata={
                        "session_id": session_id,
                        "tenant_id": tenant_id,
                        "event_count": len(events),
                        "linked_events": [e.event_id for e in events],
                    },
                )
                await self._l2.memorize(entry)

            logger.debug(
                "Compressed %d events into L2 episode (session=%s, mode=%s, type=%s, hdc=%s)",
                len(events),
                session_id,
                "llm" if self._router else "raw",
                "sovereign" if is_sovereign else "legacy",
                "active" if self._hdc else "inactive",
            )
        except (OSError, RuntimeError, ValueError, TypeError) as e:
            # Background task — never crash the main loop
            logger.error("L2 compression failed: %s", e, exc_info=True)

    async def _summarize_events(self, events: list[MemoryEvent]) -> str:
        """Summarize events using LLM Router or raw concatenation fallback."""
        raw_text = self._raw_concat(events)

        if not self._router:
            return raw_text

        # Semantic compression via CortexLLMRouter
        try:
            from cortex.llm.router import CortexPrompt
            from cortex.utils.result import Ok

            prompt = CortexPrompt(
                system_instruction=(
                    "You are a memory compression engine. Summarize the following "
                    "conversation into a concise paragraph preserving all key decisions, "
                    "technical details, errors, and outcomes. Output ONLY the summary."
                ),
                working_memory=[{"role": "user", "content": raw_text}],
                temperature=0.0,
                max_tokens=512,
            )
            result = await self._router.invoke(prompt)
            if isinstance(result, Ok):
                logger.debug("LLM compression succeeded (%d chars)", len(result.value))
                return result.value

            logger.warning("LLM compression failed: %s — falling back to raw", result.error)
        except (ValueError, TypeError, RuntimeError, OSError) as e:
            logger.warning("LLM compression error: %s — falling back to raw", e)

        return raw_text

    def get_context_vector(self) -> Any | None:
        """Return the current context as a bundled hypervector (Vector Alpha)."""
        if not self._hdc_encoder:
            return None

        events = list(self._l1._buffer)
        if not events:
            return None

        # Bundle recent interaction hypervectors
        hvs = [self._hdc_encoder.encode_text(e.content) for e in events]

        from cortex.memory.hdc.algebra import bundle

        try:
            if len(hvs) == 1:
                return hvs[0]
            return bundle(*hvs)
        except Exception as e:
            logger.warning("Context vector bundling failed: %s", e)
            return None

    @staticmethod
    def _raw_concat(events: list[MemoryEvent]) -> str:
        """Raw concatenation fallback for compression."""
        lines = [f"[{e.role}]: {e.content}" for e in events]
        return "\n".join(lines)

    # ─── Introspection ────────────────────────────────────────────

    @property
    def l1(self) -> WorkingMemoryL1:
        """Access the working memory layer."""
        return self._l1

    @property
    def l3(self) -> EventLedgerL3:
        """Access the event ledger layer."""
        return self._l3

    async def wait_for_background(self, timeout: float = 30.0) -> None:
        """Wait for background tasks to complete with a hard timeout.

        Essential for clean teardown and stable test environments.
        In test mode (CORTEX_TESTING=1), tasks are actively cancelled on timeout.
        """
        if not self._background_tasks:
            return

        import os

        _testing = os.environ.get("CORTEX_TESTING")

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._background_tasks, return_exceptions=True), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error("MemoryManager: wait_for_background timed out after %ds", timeout)
            if _testing:
                # In test mode: cancel pending tasks aggressively to prevent event loop leaks
                for task in list(self._background_tasks):
                    if not task.done():
                        task.cancel()
                self._background_tasks.clear()

    def __repr__(self) -> str:
        return f"CortexMemoryManager(l1={self._l1!r}, bg_tasks={len(self._background_tasks)})"
