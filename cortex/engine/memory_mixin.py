"""Memory mixin — Tripartite Memory (L1/L2/L3) initialization and management."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger("cortex.memory")


class MemoryMixin:
    """Cognitive Memory Subsystem (Frontera 2) for CORTEX."""

    async def _init_memory_subsystem(self, db_path: Path, conn: aiosqlite.Connection) -> None:
        """Initialize the Tripartite Cognitive Memory Architecture.

        L1 (Working Memory) + L3 (Event Ledger) always available.
        L2 (Vector Store) optional — requires qdrant_client.

        When auto_embed=False (e.g. tests), L2 initialization is skipped entirely
        to avoid loading the ML model (~30s penalty per test).
        """
        from cortex.memory.ledger import EventLedgerL3
        from cortex.memory.working import WorkingMemoryL1

        l1 = WorkingMemoryL1()
        l3 = EventLedgerL3(conn)
        await l3.ensure_table()

        # CORTOCIRCUITO: si auto_embed=False, no intentar L2 ni cargar embedder
        # Esto evita instanciar LocalEmbedder (carga modelo ML) innecesariamente.
        auto_embed = getattr(self, "_auto_embed", True)
        if not auto_embed:
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3
            logger.debug("Memory subsystem: lite (L1+L3 only, auto_embed=False)")
            return

        # L2: Optional — Qdrant may not be installed
        l2 = None
        encoder = None
        try:
            from cortex import config
            from cortex.memory.encoder import AsyncEncoder
            from cortex.memory.vector_store import VectorStoreL2

            vector_path = db_path.parent / "vectors"
            encoder = AsyncEncoder(self._get_embedder())
            l2 = VectorStoreL2(
                encoder=encoder,
                db_path=vector_path,
                url=config.QDRANT_CLOUD_URL,
                api_key=config.QDRANT_API_KEY,
            )
            logger.info("Memory L2 (VectorStore) initialized at %s", vector_path)
        except (ImportError, OSError, RuntimeError) as e:
            logger.warning("Memory L2 unavailable (degrading to L1+L3 only): %s", e)

        if l2 and encoder:
            from cortex.memory.manager import CortexMemoryManager

            self._memory_manager = CortexMemoryManager(
                l1=l1,
                l2=l2,
                l3=l3,
                encoder=encoder,
            )
        else:
            # Minimal manager: store a reference to L1+L3 for basic ops
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3

        logger.info(
            "Memory subsystem: %s",
            "full (L1+L2+L3)" if self._memory_manager else "partial (L1+L3)",
        )

    @property
    def memory(self):
        """Access the cognitive memory manager (None if not initialized)."""
        return getattr(self, "_memory_manager", None)
