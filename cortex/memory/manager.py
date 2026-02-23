# This file is part of CORTEX.
# Licensed under the Business Source License 1.1 (BSL 1.1).
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
from typing import Any

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEntry, MemoryEvent
from cortex.memory.working import WorkingMemoryL1

try:
    from cortex.memory.vector_store import VectorStoreL2
except ImportError:  # qdrant_client not installed
    VectorStoreL2 = None  # type: ignore[assignment,misc]

__all__ = ["CortexMemoryManager"]

logger = logging.getLogger("cortex.memory.manager")


class CortexMemoryManager:
    """Orchestrator for the Tripartite Cognitive Memory Architecture.

    Coordinates L1 (Working Memory), L2 (Vector Store), and L3 (Event Ledger)
    into a unified memory pipeline that never blocks the async event loop.

    Args:
        l1: Working memory instance.
        l2: Vector store instance (Qdrant-backed).
        l3: Event ledger instance (SQLite-backed).
        encoder: Async embedder for L2 vectorization.
        router: Optional LLM router for semantic compression.
    """

    __slots__ = ("_encoder", "_l1", "_l2", "_l3", "_router", "_background_tasks")

    def __init__(
        self,
        l1: WorkingMemoryL1,
        l2: VectorStoreL2,
        l3: EventLedgerL3,
        encoder: AsyncEncoder,
        router: Any | None = None,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._l3 = l3
        self._encoder = encoder
        self._router = router
        self._background_tasks: set[asyncio.Task] = set()

    # ─── Primary API ──────────────────────────────────────────────

    async def process_interaction(
        self,
        role: str,
        content: str,
        session_id: str,
        token_count: int,
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
            metadata: Optional structured metadata.

        Returns:
            The created MemoryEvent.
        """
        event = MemoryEvent(
            role=role,
            content=content,
            session_id=session_id,
            token_count=token_count,
            metadata=metadata or {},
        )

        # 1. Immutable persistence (WAL — ultra-fast)
        await self._l3.append_event(event)

        # 2. Working memory update
        overflowed = self._l1.add_event(event)

        # 3. Background compression (non-blocking)
        if overflowed:
            task = asyncio.create_task(self._compress_and_store(overflowed, session_id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return event

    async def assemble_context(
        self,
        query: str | None = None,
        max_episodes: int = 3,
    ) -> dict[str, Any]:
        """Build an optimized context for LLM injection.

        Combines L1 (recent working memory) with L2 (relevant
        past episodes retrieved via semantic search).

        Args:
            query: Optional search query for L2 retrieval.
            max_episodes: Max past episodes to retrieve.

        Returns:
            Dict with 'working_memory' and 'episodic_context' lists.
        """
        context: dict[str, Any] = {
            "working_memory": self._l1.get_context(),
            "episodic_context": [],
        }

        if query:
            try:
                episodes = await self._l2.recall(
                    query=query,
                    limit=max_episodes,
                )
                context["episodic_context"] = episodes
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("L2 recall failed (degrading gracefully): %s", e)

        return context

    # ─── Background Compression ───────────────────────────────────

    async def _compress_and_store(
        self,
        events: list[MemoryEvent],
        session_id: str,
    ) -> None:
        """Compress overflowed events and store in L2.

        Runs as a background task. When an LLM Router is configured,
        events are semantically summarized before embedding. Falls
        back to raw concatenation if no router or on LLM failure.
        """
        try:
            summary = await self._summarize_events(events)

            entry = MemoryEntry(
                content=summary,
                source="episodic",
                metadata={
                    "session_id": session_id,
                    "event_count": len(events),
                    "linked_events": [e.event_id for e in events],
                    "compression": "llm" if self._router else "raw",
                },
            )
            await self._l2.memorize(entry)

            logger.debug(
                "Compressed %d events into L2 episode (session=%s, mode=%s)",
                len(events),
                session_id,
                "llm" if self._router else "raw",
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
            from cortex.result import Ok

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

    async def wait_for_background(self) -> None:
        """Wait for all background compression tasks to complete."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    def __repr__(self) -> str:
        return f"CortexMemoryManager(l1={self._l1!r}, bg_tasks={len(self._background_tasks)})"
