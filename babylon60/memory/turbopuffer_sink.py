# [C5-REAL] Exergy-Maximized
"""
L2 Compaction Daemon: Turbopuffer Vector Sink.

Provides asynchronous, high-throughput vector offloading to Turbopuffer,
enabling cold-storage migration out of the SQLite-Vec L1 memory layer.
"""

import asyncio
import logging
import os
from typing import Any

import turbopuffer as tpuf

logger = logging.getLogger("babylon60.memory.turbopuffer")


class TurbopufferSink:
    """Asynchronous L2 Vector Sink using Turbopuffer."""

    def __init__(self, namespace: str = "cortex-l2-compaction"):
        self.namespace_name = namespace
        self._client = None
        self._ns = None

        # We don't initialize immediately to allow dynamic environment loading
        self._initialized = False

    def _ensure_init(self) -> None:
        """Lazy initialization of the tpuf client."""
        if self._initialized:
            return

        api_key = os.environ.get("TURBOPUFFER_API_KEY")
        if not api_key:
            logger.warning(
                "[TurbopufferSink] TURBOPUFFER_API_KEY not found. "
                "The sink will fail on write operations."
            )
            return

        self._client = tpuf.Turbopuffer(api_key=api_key)
        self._ns = self._client.namespace(self.namespace_name)
        self._initialized = True
        logger.info(f"[TurbopufferSink] Initialized namespace: {self.namespace_name}")

    async def flush_batch(self, vectors: list[dict[str, Any]]) -> bool:
        """
        Asynchronously flush a batch of vectors to Turbopuffer.
        Expects a list of dictionaries with keys: 'id', 'vector', and 'attributes'/'category' etc.
        Must not block the GIL (INV_ASYNC_STRICT).
        """
        self._ensure_init()
        if not self._initialized or not self._ns:
            logger.error("[TurbopufferSink] Cannot flush batch: Not initialized.")
            return False

        if not vectors:
            return True

        # Run the synchronous tpuf network call in a threadpool to prevent GIL lock
        def _do_write():
            assert self._ns is not None
            self._ns.write(upsert_rows=vectors)

        try:
            logger.info(f"[TurbopufferSink] Flushing batch of {len(vectors)} vectors to L2...")
            await asyncio.to_thread(_do_write)
            logger.info("[TurbopufferSink] Batch flush complete.")
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"[TurbopufferSink] Failed to flush batch: {e}")
            return False
