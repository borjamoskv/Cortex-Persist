from __future__ import annotations

from typing import Any

from cortex.compaction.mem0_pipeline import Mem0Pipeline

try:
    import structlog
    _HAS_STRUCTLOG = True
    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:
    import logging
    _HAS_STRUCTLOG = False
    logger = logging.getLogger(__name__)


def log_info(msg: str, **kwargs: Any) -> None:
    if _HAS_STRUCTLOG:
        logger.info(msg, **kwargs)
    else:
        logger.info("%s %s", msg, kwargs)


class MemoryOS:
    """CORTEX Memory OS Policy Layer.

    Orchestrates EPISODIC → SEMANTIC flow via Mem0Pipeline.
    When an engine reference is provided, gc() delegates to the
    Memento specialist for real compaction (Cable 4 lifecycle).
    """

    def __init__(
        self,
        exergy_threshold: float = 0.5,
        engine: Any | None = None,
    ) -> None:
        self.pipeline = Mem0Pipeline(exergy_threshold=exergy_threshold)
        self._engine = engine

    async def persist_episodic_to_semantic(self, context: str) -> int:
        """Extract semantic facts from episodic context and persist."""
        log_info("MemoryOS: Starting episodic-to-semantic persistence")

        facts = await self.pipeline.extract(context)
        if not facts:
            log_info("MemoryOS: No facts extracted from context")
            return 0

        consolidated = await self.pipeline.consolidate(facts)
        stored_count = await self.pipeline.store(consolidated)

        log_info("MemoryOS: Persistence complete", stored_facts=stored_count)
        return stored_count

    async def gc(self) -> None:
        """Thermodynamic GC — delegates to Memento agent when available."""
        log_info("MemoryOS: Running thermodynamic compaction (GC)")

        if self._engine and hasattr(self._engine, "_memento_agent"):
            agent = self._engine._memento_agent
            if agent is not None:
                await agent.compact()
                log_info("MemoryOS: GC delegated to Memento specialist")
                return

        log_info("MemoryOS: No Memento agent — GC skipped")
