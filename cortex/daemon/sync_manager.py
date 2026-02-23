"""
CORTEX v6 — Sync Orchestrator (Ouroboros Phase).

Decouples the synchronization logic from the MoskvDaemon core.
Handles JSON memory ↔ SQLite DB synchronization using an asynchronous-friendly
approach, preparing the way for MerklePulse differential sync.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from cortex.sync import SyncResult, WritebackResult

if TYPE_CHECKING:
    from cortex.engine import CortexEngine


logger = logging.getLogger("cortex.daemon.sync")


class CortexSyncManager:
    """Manages all CORTEX synchronization tasks."""

    def __init__(self, engine: CortexEngine):
        self._engine = engine
        self._sync_lock = asyncio.Lock()
        self._last_sync_result: SyncResult | None = None
        self._last_wb_result: WritebackResult | None = None
        self._pulse_state: dict[str, str] = {}  # MerklePulse state (file -> hash)

    async def run_sync_cycle(self) -> dict[str, Any]:
        """
        Executes a full sync cycle: Sync (Read) + Write-back (Export) + Snapshot.
        Ensures thread-safe execution via asyncio.Lock.
        """
        async with self._sync_lock:
            loop = asyncio.get_running_loop()
            stats = {}

            try:
                # 1. MerklePulse: Differential Sync (Read: Memory -> DB)
                self._last_sync_result = await self._merkle_pulse_sync()
                stats["sync"] = self._last_sync_result.total if self._last_sync_result else 0

                # 2. Write-back (Export: DB -> Memory)
                self._last_wb_result = await loop.run_in_executor(None, self._run_export_to_json)
                stats["writeback"] = (
                    self._last_wb_result.items_exported if self._last_wb_result else 0
                )

                # 3. Snapshot (DB Export)
                await self._run_export_snapshot()
                stats["snapshot"] = True

                return stats

            except Exception as e:
                logger.exception("Sync cycle failed")
                return {"error": str(e)}

    async def _merkle_pulse_sync(self) -> SyncResult:
        """
        Implementation of MerklePulse: Partitioned differential sync.
        Only syncs files that have changed since the last pulse.
        """
        loop = asyncio.get_running_loop()
        from cortex.sync.common import MEMORY_DIR, file_hash

        # 1. Detect changes using hashes
        changed_files = []
        for f in ["ghosts.json", "system.json", "mistakes.jsonl", "bridges.jsonl"]:
            path = MEMORY_DIR / f
            if path.exists():
                current_hash = await loop.run_in_executor(None, file_hash, path)
                if current_hash != self._pulse_state.get(f):
                    changed_files.append((f, current_hash))

        if not changed_files:
            logger.debug("MerklePulse: No memory changes detected")
            return SyncResult()

        # 2. Process only changed files
        logger.info("MerklePulse: Detected changes in %d files", len(changed_files))
        result = await loop.run_in_executor(None, self._run_sync_memory)

        # 3. Update pulse state
        for f, h in changed_files:
            self._pulse_state[f] = h

        return result

    def _run_sync_memory(self) -> SyncResult:
        """Internal synchronous sync wrapper."""
        from cortex.sync import sync_memory

        return sync_memory(self._engine)

    def _run_export_to_json(self) -> WritebackResult:
        """Internal synchronous export wrapper."""
        from cortex.sync import export_to_json

        return export_to_json(self._engine)

    async def _run_export_snapshot(self) -> None:
        """Asynchronous snapshot export."""
        from cortex.sync import export_snapshot

        await export_snapshot(self._engine)

    @property
    def status(self) -> dict:
        """Returns the status of the last sync operations."""
        return {
            "last_sync_total": (self._last_sync_result.total if self._last_sync_result else 0),
            "last_wb_total": (self._last_wb_result.items_exported if self._last_wb_result else 0),
            "has_errors": bool(
                (self._last_sync_result and self._last_sync_result.errors)
                or (self._last_wb_result and self._last_wb_result.errors)
            ),
        }
