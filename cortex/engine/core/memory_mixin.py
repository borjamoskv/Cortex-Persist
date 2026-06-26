# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase

__all__ = ["MemoryMixin"]

logger = logging.getLogger("cortex.memory")


class MemoryMixin(EngineMixinBase):
    """Cognitive Memory Subsystem (Frontera 2) - Tripartite L1/L2/L3 Architecture.

    L1 (Working Memory): In-process ephemeral buffer with access frequency tracking.
    L2 (Vector Store): Sovereign sqlite-vec ANN index + optional HDC hypervectors.
    L3 (Event Ledger): Append-only temporal event log for causal replay.

    Initialization is lazy: L2/HDC are skipped when ``auto_embed=False``
    to avoid the ~30s ML model load penalty during tests.
    """

    async def _init_memory_subsystem(self, db_path: Path, conn: aiosqlite.Connection) -> None:
        """Initialize the Tripartite Cognitive Memory Architecture."""
        l1, l3 = await self._init_core_memory(conn)
        if l1 is None or l3 is None:
            self._set_memory_state(None, None, None)
            return

        bus = self._init_signal_bus()

        l2_result = self._init_vector_memory(db_path, l1, l3)
        if not l2_result.get("proceed"):
            self._set_memory_state(None, l1, l3)
            logger.info("Memory subsystem: partial (L1+L3) (%s)", l2_result.get("reason", ""))
            return

        l2, encoder, hdc_l2, hdc_encoder = l2_result["components"]

        if l2 and encoder:
            self._init_memory_manager(l1, l2, l3, encoder, hdc_l2, hdc_encoder, bus)
        else:
            self._set_memory_state(None, l1, l3)

        self._memory_ready = True
        self._log_memory_status(hdc_l2 is not None, l2_result.get("l2_skip_reason"))

    async def _init_core_memory(self, conn: aiosqlite.Connection):
        try:
            import os

            from cortex.memory.ledger import EventLedgerL3

            redis_url = os.environ.get("CORTEX_REDIS_URL")
            if redis_url:
                from cortex.memory.redis_working import RedisWorkingMemoryL1

                l1 = RedisWorkingMemoryL1(redis_url=redis_url)
                logger.info("Memory L1 (RedisWorkingMemoryL1) initialized at %s", redis_url)
            else:
                from cortex.memory.working import WorkingMemoryL1

                l1 = WorkingMemoryL1()
            l3 = EventLedgerL3(conn)
            await l3.ensure_table()
            return l1, l3
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.warning("Memory L1/L3 unavailable: %s", e)
            return None, None

    def _init_signal_bus(self):
        try:
            from cortex_extensions.signals.bus import SignalBus

            sync_conn = self._get_sync_conn()
            bus = SignalBus(sync_conn)
            bus.ensure_table()
            return bus
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.warning("SignalBus initialization failed: %s", e)
            return None

    def _init_vector_memory(self, db_path: Path, l1, l3) -> dict:
        import os

        use_hdc = os.environ.get("CORTEX_HDC") == "1"
        try:
            import numpy  # noqa: F401

            numpy_installed = True
        except ImportError:
            numpy_installed = False

        if not getattr(self, "_vec_available", False):
            return {"proceed": False, "reason": "optional L2 skipped: sqlite-vec unavailable"}
        if not numpy_installed:
            return {"proceed": False, "reason": "optional L2 skipped: numpy not installed"}

        auto_embed = getattr(self, "_auto_embed", True)
        if not auto_embed or os.environ.get("CORTEX_NO_EMBED") == "1":
            return {"proceed": False, "reason": "auto_embed=False"}

        l2, encoder, l2_skip_reason = self._init_l2_dense(db_path)
        hdc_l2, hdc_encoder = self._init_hdc(db_path) if use_hdc else (None, None)

        return {
            "proceed": True,
            "components": (l2, encoder, hdc_l2, hdc_encoder),
            "l2_skip_reason": l2_skip_reason,
        }

    def _init_l2_dense(self, db_path: Path):
        l2, encoder, l2_skip_reason = None, None, None
        try:
            from cortex.memory.encoder import AsyncEncoder
            from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

            vector_path = db_path.parent / "vectors"
            encoder = AsyncEncoder(self._get_embedder())
            l2 = SovereignVectorStoreL2(encoder=encoder, db_path=vector_path / "vectors.db")
            logger.info("Memory L2 (SovereignVectorStoreL2) initialized at %s", vector_path)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            if isinstance(e, ImportError | ModuleNotFoundError) or "numpy" in str(e).lower():
                l2_skip_reason = str(e)
            else:
                logger.warning("Memory L2 unavailable (degrading to L1+L3 only): %s", e)
        return l2, encoder, l2_skip_reason

    def _init_hdc(self, db_path: Path):
        hdc_l2, hdc_encoder = None, None
        try:
            from cortex.memory.hdc import HDCEncoder, HDCVectorStoreL2, ItemMemory

            hdc_path = db_path.parent / "hdc"
            item_mem = ItemMemory(codebook_path=hdc_path / "codebook.json")
            hdc_encoder = HDCEncoder(item_mem)
            hdc_l2 = HDCVectorStoreL2(
                encoder=hdc_encoder, item_memory=item_mem, db_path=hdc_path / "hdc.db"
            )
            logger.info("Vector Alpha (HDC) initialized at %s", hdc_path)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.warning("Vector Alpha (HDC) initialization failed: %s", e)
        return hdc_l2, hdc_encoder

    def _init_memory_manager(self, l1, l2, l3, encoder, hdc_l2, hdc_encoder, bus):
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
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.warning("Memory manager unavailable: %s", e)
            self._set_memory_state(None, l1, l3)

    def _set_memory_state(self, manager, l1, l3):
        self._memory_manager = manager
        self._memory_l1 = l1
        self._memory_l3 = l3
        self._memory_ready = True

    def _log_memory_status(self, has_hdc: bool, skip_reason: str | None):
        if self._memory_manager:
            logger.info(
                "Memory subsystem: full (L1+L2+L3) (HDC: %s)", "active" if has_hdc else "inactive"
            )
        elif skip_reason:
            logger.info(
                "Memory subsystem: partial (L1+L3) (HDC: %s, optional L2 skipped: %s)",
                "active" if has_hdc else "inactive",
                skip_reason,
            )
        else:
            logger.info(
                "Memory subsystem: partial (L1+L3) (HDC: %s)", "active" if has_hdc else "inactive"
            )

    @property
    def memory(self):
        """Access the cognitive memory manager (None if not initialized)."""
        return getattr(self, "_memory_manager", None)
