"""Swarm Manager — Singleton for tracking ephemeral worktree state.

This module provides a registry for active git worktrees and their
associated metadata, bridging the stateless REST API with the
stateful worktree_isolation context managers.
"""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortex.extensions.swarm.worktree_isolation import isolated_worktree

logger = logging.getLogger("cortex.swarm.manager")


class WorktreeState:
    """Metadata for an active or pending worktree."""

    def __init__(self, worktree_id: str, branch_name: str, path: Path):
        self.id = worktree_id
        self.branch_name = branch_name
        self.path = path
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "provisioning"
        self.pid = os.getpid()
        self.task: asyncio.Task | None = None


class SwarmManager:
    """Orchestrates ephemeral workspaces and agent health."""

    def __init__(self):
        self.worktrees: dict[str, WorktreeState] = {}
        self._lock = asyncio.Lock()
        logger.info("SwarmManager initialized: %s", id(self))

    async def _trigger_auto_compaction(self, worktree_id: str) -> None:
        """Axiom Ω₃: Enforce thermodynamic compaction on the worktree state."""
        logger.info("SwarmManager: Triggering Auto-Compaction for %s", worktree_id)
        # TODO: Integrate with TokenReducer or actual process compaction
        pass

    async def create_worktree(
        self, branch_name: str, base_path: str | None = None
    ) -> WorktreeState:
        """Provision a new isolated worktree."""
        worktree_id = str(uuid.uuid4())[:8]
        state = WorktreeState(worktree_id, branch_name, Path("/tmp/pending"))
        ready_event = asyncio.Event()

        # Phase 0: Thermodynamic Cleanup (Axiom Ω₃)
        await self._trigger_auto_compaction(worktree_id)

        async def _lifecycle():
            try:
                async with isolated_worktree(branch_name, base_path) as path:
                    state.path = path
                    state.status = "active"
                    ready_event.set()
                    logger.info("Worktree %s active at %s", worktree_id, path)
                    while state.status == "active":
                        await asyncio.sleep(0.1)
            except Exception as e:
                state.status = "failed"
                ready_event.set()
                logger.error("Worktree %s lifecycle failed: %s", worktree_id, e)
            finally:
                state.status = "destroyed"
                async with self._lock:
                    if worktree_id in self.worktrees:
                        del self.worktrees[worktree_id]

        async with self._lock:
            self.worktrees[worktree_id] = state

        state.task = asyncio.create_task(_lifecycle())

        # Wait for the worktree to be actually created or fail
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            state.status = "failed"
            logger.error("Worktree %s creation timed out", worktree_id)

        return state

    async def get_worktree(self, worktree_id: str) -> WorktreeState | None:
        """Retrieve worktree metadata."""
        async with self._lock:
            res = self.worktrees.get(worktree_id)
            if not res:
                logger.warning(
                    "Worktree %s not found in %s", worktree_id, list(self.worktrees.keys())
                )
            return res

    async def delete_worktree(self, worktree_id: str) -> bool:
        """Cleanly shutdown an isolated worktree."""
        async with self._lock:
            state = self.worktrees.get(worktree_id)
            if not state:
                return False

            state.status = "tearing_down"
            # The _lifecycle loop will now exit and trigger __aexit__
            return True

    async def get_status(self) -> dict[str, Any]:
        """Aggregate swarm health and load."""
        async with self._lock:
            return {
                "active_worktrees": len(
                    [w for w in self.worktrees.values() if w.status == "active"]
                ),
                "total_worktrees": len(self.worktrees),
                "agent_pids": list(set(w.pid for w in self.worktrees.values())),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


_manager_key = "__cortex_swarm_manager__"


def get_swarm_manager() -> SwarmManager:
    """True singleton provider for SwarmManager."""
    if not hasattr(sys, _manager_key):
        setattr(sys, _manager_key, SwarmManager())
    return getattr(sys, _manager_key)
