# [C5-REAL] Exergy-Maximized
"""
Autonomous Ignition Daemon (Macrófago Autónomo)
Listens to WatchdogHub events (fs.modified) and triggers zero-prompt evolution or git sentinel.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from babylon60.engine import CortexEngine
from babylon60.extensions.daemon.zero_prompting import ZeroPromptingDaemon

logger = logging.getLogger("babylon60.daemon.autonomous_ignition")


class AutonomousIgnitionDaemon:
    def __init__(self, engine: CortexEngine, event_bus: Any, workspace_root: str):
        self.engine = engine
        self.event_bus = event_bus
        self.workspace_root = workspace_root
        self.zero_prompt = ZeroPromptingDaemon(engine, workspace_root)
        self._running = False

    async def start(self) -> None:
        self._running = True
        if hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("fs.modified", self._on_fs_modified)
            self.event_bus.subscribe("fs.created", self._on_fs_modified)
        logger.info("AutonomousIgnitionDaemon started. Listening to WatchdogHub events.")

    async def stop(self) -> None:
        self._running = False
        logger.info("AutonomousIgnitionDaemon stopped.")

    async def _on_fs_modified(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._running:
            return

        path = payload.get("path", "unknown")
        # Ignore git internal modifications
        if ".git" in Path(path).parts:
            return

        logger.info(
            "AutonomousIgnition: Detected mutation on %s. Triggering C5-REAL validation.", path
        )

        try:
            asyncio.create_task(self._process_mutation(path))
        except Exception as e:
            logger.error(
                "AutonomousIgnition: Failed to spawn mutation processing for %s: %s", path, e
            )

    async def _process_mutation(self, path: str) -> None:
        """Process the file mutation using Zero-Prompt evolution and Git Sentinel."""
        logger.debug("Processing mutation for: %s", path)
        # 1. Run zero prompt cycle focusing on this path's entropy
        await self.zero_prompt.evolution_cycle(focus=path)

        # 2. Invoke Git Sentinel
        from babylon60.extensions.git.git_sentinel import GitSentinel

        sentinel = GitSentinel(self.workspace_root)
        await sentinel.silent_commit(path)
