"""GhostWatcher — Optimized Cognitive Stratification.

Listens to GHOST_DETECTED mutations in Nexus and triggers GHOST_WATCH_TRIGGER
if they meet a certain threshold of significance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex.nexus_v8 import DomainOrigin, IntentType, NexusWorldModel, WorldMutation

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.watcher")


class GhostWatcher:
    """Reactive monitor for world model ghosts and state drift."""

    def __init__(self, nexus: NexusWorldModel, engine: AsyncCortexEngine):
        self._nexus = nexus
        self._engine = engine
        self._is_active = False

    def start(self) -> None:
        """Subscribe to GHOST_DETECTED and start watching."""
        if self._is_active:
            return
        self._is_active = True
        self._nexus.on(IntentType.GHOST_DETECTED, self._on_ghost_detected)
        logger.info("[WATCHER] GhostWatcher activated on Nexus bus.")

    async def _on_ghost_detected(self, mutation: WorldMutation) -> None:
        """Triggered when a ghost is detected on any domain."""
        ghost_ref = mutation.payload.get("reference", "unknown")
        project = mutation.project

        logger.info("[WATCHER] Analyzing ghost resonance: %s in %s", ghost_ref, project)

        # 1. Check CORTEX memory: Is this ghost already being tracked?
        facts = await self._engine.search(f"ghost: {ghost_ref}", project=project, top_k=1)

        if facts and facts[0].score > 0.85:
            logger.debug("[WATCHER] Ghost %s already tracked (Score=%.2f). Skipping trigger.",
                         ghost_ref, facts[0].score)
            return

        # 2. If it's a new high-entropy ghost, fire the trigger
        logger.warning("[WATCHER] CRITICAL GHOST DETECTED: %s. Firing trigger pulse.", ghost_ref)
        await self._nexus.mutate(WorldMutation(
            origin=DomainOrigin.CORTEX_CORE,
            intent=IntentType.GHOST_WATCH_TRIGGER,
            project=project,
            priority=mutation.priority,
            payload={
                "reference": ghost_ref,
                "original_mutation_key": mutation.idempotency_key,
                "action_required": "Track and verify entity existence",
            }
        ))

    def stop(self) -> None:
        """Stop watching."""
        self._is_active = False
        logger.info("[WATCHER] GhostWatcher deactivated.")
