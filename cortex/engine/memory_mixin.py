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
        from cortex.signals.bus import SignalBus

        l1 = WorkingMemoryL1()
        l3 = EventLedgerL3(conn)
        await l3.ensure_table()

        # Dedicated sync connection for the SignalBus (L1 Consciousness)
        bus = None
        try:
            # We use the engine's _get_sync_conn if available, or create one.
            # MemoryMixin is part of CortexEngine, so we can use self._get_sync_conn()
            sync_conn = self._get_sync_conn()  # type: ignore[reportAttributeAccessIssue]
            bus = SignalBus(sync_conn)
            bus.ensure_table()
        except Exception as e:
            logger.warning("SignalBus initialization failed: %s", e)

        # v7 (G10): HDC is opt-in by default.
        import os

        use_hdc = os.environ.get("CORTEX_HDC") == "1"

        # CORTOCIRCUITO: si auto_embed=False, no intentar L2 ni cargar embedder
        # Esto evita instanciar LocalEmbedder (carga modelo ML) innecesariamente.
        auto_embed = getattr(self, "_auto_embed", True)
        if not auto_embed:
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3
            logger.debug("Memory subsystem: lite (L1+L3 only, auto_embed=False)")
            return

        # 1. Dense L2: Sovereign (v6) Vector Store (SQLite-vec)
        l2 = None
        encoder = None
        try:
            from cortex.memory.encoder import AsyncEncoder
            from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

            vector_path = db_path.parent / "vectors"
            encoder = AsyncEncoder(self._get_embedder())  # type: ignore[reportAttributeAccessIssue]
            l2 = SovereignVectorStoreL2(encoder=encoder, db_path=vector_path / "vectors.db")

            logger.info("Memory L2 (SovereignVectorStoreL2) initialized at %s", vector_path)
        except (ImportError, OSError, RuntimeError) as e:
            logger.warning("Memory L2 unavailable (degrading to L1+L3 only): %s", e)

        # 2. Vector Alpha (HDC/v7): Now primary.
        hdc_l2 = None
        hdc_encoder = None
        if use_hdc:
            try:
                from cortex.memory.hdc import HDCEncoder, HDCVectorStoreL2, ItemMemory

                hdc_path = db_path.parent / "hdc"
                item_mem = ItemMemory(codebook_path=hdc_path / "codebook.json")
                hdc_encoder = HDCEncoder(item_mem)
                hdc_l2 = HDCVectorStoreL2(
                    encoder=hdc_encoder, item_memory=item_mem, db_path=hdc_path / "hdc.db"
                )
                logger.info("Vector Alpha (HDC) initialized at %s", hdc_path)
            except (ImportError, OSError, RuntimeError) as e:
                logger.warning("Vector Alpha (HDC) initialization failed: %s", e)

        if l2 and encoder:
            from cortex.memory.manager import CortexMemoryManager

            self._memory_manager = CortexMemoryManager(
                l1=l1,
                l2=l2,
                l3=l3,
                encoder=encoder,
                hdc_l2=hdc_l2,
                hdc_encoder=hdc_encoder,
                bus=bus,
            )
        else:
            # Minimal manager: store a reference to L1+L3 for basic ops
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3

        logger.info(
            "Memory subsystem: %s (HDC: %s)",
            "full (L1+L2+L3)" if self._memory_manager else "partial (L1+L3)",
            "active" if hdc_l2 else "inactive",
        )

    @property
    def memory(self):
        """Access the cognitive memory manager (None if not initialized)."""
        return getattr(self, "_memory_manager", None)
