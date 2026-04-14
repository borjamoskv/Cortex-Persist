"""Memory mixin — Tripartite Memory (L1/L2/L3) initialization and management."""

from __future__ import annotations

import logging
from importlib.util import find_spec
from pathlib import Path

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase

__all__ = ["MemoryMixin"]

logger = logging.getLogger("cortex.memory")


class MemoryMixin(EngineMixinBase):
    """Cognitive Memory Subsystem (Frontera 2) — Tripartite L1/L2/L3 Architecture.

    L1 (Working Memory): In-process ephemeral buffer with access frequency tracking.
    L2 (Vector Store): Sovereign sqlite-vec ANN index + optional HDC hypervectors.
    L3 (Event Ledger): Append-only temporal event log for causal replay.

    Initialization is lazy: L2/HDC are skipped when ``auto_embed=False``
    to avoid the ~30s ML model load penalty during tests.
    """

    async def _init_memory_subsystem(self, db_path: Path, conn: aiosqlite.Connection) -> None:
        """Initialize the Tripartite Cognitive Memory Architecture.

        L1 (Working Memory) + L3 (Event Ledger) always available.
        L2 (Vector Store) optional — requires qdrant_client.

        When auto_embed=False (e.g. tests), L2 initialization is skipped entirely
        to avoid loading the ML model (~30s penalty per test).
        """
        try:
            from cortex.memory.ledger import EventLedgerL3
            from cortex.memory.working import WorkingMemoryL1
        except Exception as e:  # noqa: BLE001
            self._memory_manager = None
            self._memory_l1 = None
            self._memory_l3 = None
            self._memory_ready = True
            logger.warning("Memory L1/L3 unavailable (degrading to no memory subsystem): %s", e)
            return

        l1 = WorkingMemoryL1()
        l3 = EventLedgerL3(conn)
        await l3.ensure_table()

        # Dedicated sync connection for the SignalBus (L1 Consciousness)
        bus = None
        try:
            from cortex.extensions.signals.bus import SignalBus

            # We use the engine's _get_sync_conn if available, or create one.
            # MemoryMixin is part of CortexEngine, so we can use self._get_sync_conn()
            sync_conn = self._get_sync_conn()
            bus = SignalBus(sync_conn)
            bus.ensure_table()
        except Exception as e:  # noqa: BLE001
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
            self._memory_ready = True
            logger.debug("Memory subsystem: lite (L1+L3 only, auto_embed=False)")
            return

        if not getattr(self, "_vec_available", False):
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3
            self._memory_ready = True
            logger.info("Memory subsystem: partial (L1+L3) (optional L2 skipped: sqlite-vec unavailable)")
            return

        if find_spec("numpy") is None:
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3
            self._memory_ready = True
            logger.info("Memory subsystem: partial (L1+L3) (optional L2 skipped: numpy not installed)")
            return

        # 1. Dense L2: Sovereign (v6) Vector Store (SQLite-vec)
        l2 = None
        encoder = None
        l2_skip_reason: str | None = None
        try:
            from cortex.memory.encoder import AsyncEncoder
            from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

            vector_path = db_path.parent / "vectors"
            encoder = AsyncEncoder(self._get_embedder())
            l2 = SovereignVectorStoreL2(encoder=encoder, db_path=vector_path / "vectors.db")

            logger.info("Memory L2 (SovereignVectorStoreL2) initialized at %s", vector_path)
        except Exception as e:  # noqa: BLE001
            if isinstance(e, (ImportError, ModuleNotFoundError)) or "numpy" in str(e).lower():
                l2_skip_reason = str(e)
            else:
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
            except Exception as e:  # noqa: BLE001
                logger.warning("Vector Alpha (HDC) initialization failed: %s", e)

        if l2 and encoder:
            try:
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
            except Exception as e:  # noqa: BLE001
                logger.warning("Memory manager unavailable (degrading to L1+L3 only): %s", e)
                self._memory_manager = None
                self._memory_l1 = l1
                self._memory_l3 = l3
        else:
            # Minimal manager: store a reference to L1+L3 for basic ops
            self._memory_manager = None
            self._memory_l1 = l1
            self._memory_l3 = l3

        self._memory_ready = True

        if self._memory_manager:
            logger.info("Memory subsystem: full (L1+L2+L3) (HDC: %s)", "active" if hdc_l2 else "inactive")
        elif l2_skip_reason:
            logger.info(
                "Memory subsystem: partial (L1+L3) (HDC: %s, optional L2 skipped: %s)",
                "active" if hdc_l2 else "inactive",
                l2_skip_reason,
            )
        else:
            logger.info(
                "Memory subsystem: partial (L1+L3) (HDC: %s)",
                "active" if hdc_l2 else "inactive",
            )

    @property
    def memory(self):
        """Access the cognitive memory manager (None if not initialized)."""
        return getattr(self, "_memory_manager", None)
