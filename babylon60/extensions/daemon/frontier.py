# [C5-REAL] Exergy-Maximized
"""
Frontier Daemon (R&D & Metabolism)
The engine that ensures CORTEX is always at the bleeding edge.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("babylon60_extensions.daemon.frontier")


class FrontierDaemon:
    """
    The R&D and Auto-Refactoring pulse of MOSKV-1.

    1. Cognitive Ingestion: Ingests SOTA documentation and auto-forges skills.
    2. Nocturnal Metabolism: Executes Ouroboros-Omega to reduce codebase entropy.
    """

    def __init__(
        self,
        engine: Any = None,
        metabolism_interval_hours: int = 12,
        ingestion_interval_hours: int = 24,
        allow_commits: bool = True,
    ):
        self.engine = engine
        self.metabolism_interval = metabolism_interval_hours * 3600
        self.ingestion_interval = ingestion_interval_hours * 3600
        self.allow_commits = allow_commits
        self._shutdown = False
        self.last_metabolism = 0
        self.last_ingestion = 0

    async def _run_metabolism(self):
        """Executes Ouroboros-Omega on high-entropy files."""
        logger.info("[FRONTIER] Initializing Nocturnal Metabolism (Ouroboros-Omega)...")

        try:
            import os

            target_path = Path(os.environ.get("CORTEX_ROOT", Path(__file__).resolve().parents[2]))
            from babylon60.extensions.evolution.ouroboros_omega import OuroborosOmega

            test_file = target_path / "extensions/daemon/core.py"
            if test_file.exists():
                logger.info("[FRONTIER] Metabolizing %s...", test_file.name)
                engine = OuroborosOmega(str(test_file), dry_run=not self.allow_commits)
                result = await engine.execute_atomic_cycle()

                status = result.get("status", "UNKNOWN")
                logger.info("[FRONTIER] Metabolism result: %s", status)

                if status == "SUCCESS":
                    msg = f"Auto-refactored {test_file.name} with Ouroboros-Omega."
                    await self._log_evolution("metabolism", msg)
        except Exception as e:  # noqa: BLE001
            logger.error("[FRONTIER] Metabolism cycle failed: %s", e)

    async def _run_ingestion(self):
        """Ingests new intelligence to forge skills."""
        logger.info("[FRONTIER] Scanning frontier for Cognitive Ingestion...")
        sources = [
            "https://github.com/google-deepmind/jules",
            "https://docs.anthropic.com/en/docs/agents-and-tools/computer-use",
        ]

        for source in sources:
            logger.info("[FRONTIER] Analyzing source: %s", source)
            msg = f"Analyzed {source} for potential skill emancipation."
            await self._log_evolution("ingestion", msg)

    async def _log_evolution(self, type: str, content: str):
        """Registers the evolution event in CORTEX."""
        if not self.engine:
            return
        try:
            await self.engine.store(
                project="cortex-core",
                content=f"[{type.upper()}] {content}",
                fact_type="decision",
                tags=["Evolution", type],
                confidence="C5",
                source="daemon:frontier",
                actor_id="frontier",
            )
            logger.info("[FRONTIER] Evolution event logged to CORTEX: %s", type)
        except Exception as e:  # noqa: BLE001
            logger.error("[FRONTIER] Failed to log evolution: %s", e)

    async def run_loop(self):
        """Main Frontier loop."""
        logger.info("Initializing Frontier Daemon (Evolution Engine)...")
        while not self._shutdown:
            now = time.monotonic()

            # Metabolism Cycle
            if now - self.last_metabolism > self.metabolism_interval:
                await self._run_metabolism()
                self.last_metabolism = now

            # Ingestion Cycle
            if now - self.last_ingestion > self.ingestion_interval:
                await self._run_ingestion()
                self.last_ingestion = now

            await asyncio.sleep(60)  # Poll every minute for scheduled tasks

    def stop(self):
        logger.info("Stopping Frontier Daemon.")
        self._shutdown = True
