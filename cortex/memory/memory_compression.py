# [C5-REAL] Exergy-Maximized
# NOTE: This module is the async L1→L2 overflow pipeline.
#       For the stateless MDL-based fact fusion compressor, see compression.py.
"""memory_compression — Background L1 Overflow Compression Pipeline.

Async pipeline extracted from CortexMemoryManager (Landauer LOC barrier ≤500).
Handles 'Sleep-time Compute': overflowed L1 events are compressed (LLM or raw)
and persisted to L2 in a bounded background asyncio task.

Distinct from ``compression.py`` which provides stateless, synchronous
semantic MDL compression for batch engram fusion.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.memory.manager import CortexMemoryManager
    from cortex.memory.models import MemoryEvent

__all__ = [
    "compress_and_store",
    "raw_concat",
    "summarize_events",
]

logger = logging.getLogger("cortex.memory.compression")


def raw_concat(events: list[MemoryEvent]) -> str:
    """Raw concatenation fallback for compression - O(N), no LLM required."""
    return "\n".join(f"[{e.role}]: {e.content}" for e in events)


async def summarize_events(
    manager: CortexMemoryManager,
    events: list[MemoryEvent],
) -> str:
    """Summarize events using LLM Router or raw concatenation fallback."""
    raw_text = raw_concat(events)

    if not manager._router:
        return raw_text

    try:
        from cortex.utils.result import Ok
        from cortex_extensions.llm.router import CortexPrompt

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
        result = await manager._router.invoke(prompt)
        if isinstance(result, Ok):
            logger.debug("LLM compression succeeded (%d chars)", len(result.value))
            return result.value

        logger.warning("LLM compression failed: %s - falling back to raw", result.error)
    except (ValueError, TypeError, RuntimeError, OSError, ImportError) as e:
        logger.warning("LLM compression error: %s - falling back to raw", e)

    return raw_text


async def compress_and_store(
    manager: CortexMemoryManager,
    events: list[MemoryEvent],
    session_id: str,
    tenant_id: str,
    project_id: str,
) -> None:
    """Compress overflowed events and store in L2 (v6 sovereign or legacy).

    Called as a background asyncio.Task - must NEVER raise.
    """
    try:
        from cortex.memory.models import CortexFactModel, MemoryEntry

        summary = await summarize_events(manager, events)
        is_sovereign = manager._l2.__class__.__name__ == "SovereignVectorStoreL2"

        if is_sovereign:
            vector = await manager._encoder.encode(summary)

            _meta: dict[str, Any] = {
                "session_id": session_id,
                "event_count": len(events),
                "linked_events": [e.event_id for e in events],
                "compression": "llm" if manager._router else "raw",
            }
            fact = CortexFactModel(
                id=uuid.uuid4().hex,
                tenant_id=tenant_id,
                project_id=project_id,
                content=summary,
                embedding=vector,
                timestamp=time.monotonic(),
                cognitive_layer="episodic",
                metadata=_meta,
            )
            await manager._l2.memorize(fact)
            if manager._hdc:
                await manager._hdc.memorize(fact)
        else:
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
            await manager._l2.memorize(entry)

        logger.debug(
            "Compressed %d events into L2 episode (session=%s, mode=%s, type=%s, hdc=%s)",
            len(events),
            session_id,
            "llm" if manager._router else "raw",
            "sovereign" if is_sovereign else "legacy",
            "active" if manager._hdc else "inactive",
        )
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        logger.exception("L2 compression failed: %s", e)
