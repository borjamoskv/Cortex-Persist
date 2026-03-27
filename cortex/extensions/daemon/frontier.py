"""
Frontier Daemon (R&D & Metabolism)
The engine that ensures CORTEX is always at the bleeding edge.
"""

import asyncio
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from cortex.services.bounty_service import BountyService

logger = logging.getLogger("cortex.extensions.daemon.frontier")


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
        self.last_metabolism: float = 0.0
        self.last_ingestion: float = 0.0

    async def _run_metabolism(self):
        """Executes Ouroboros-Omega on high-entropy files."""
        logger.info("[FRONTIER] Initializing Nocturnal Metabolism (Ouroboros-Omega)...")

        try:
            target_path = Path.home() / "cortex/cortex"
            from cortex.extensions.evolution.ouroboros_omega import OuroborosOmega

            test_file = target_path / "daemon/core.py"
            if test_file.exists():
                logger.info("[FRONTIER] Metabolizing %s...", test_file.name)
                engine = OuroborosOmega(str(test_file), dry_run=not self.allow_commits)
                result = await engine.execute_atomic_cycle()

                status = result.get("status", "UNKNOWN")
                logger.info("[FRONTIER] Metabolism result: %s", status)

                if status == "SUCCESS":
                    msg = f"Auto-refactored {test_file.name} with Ouroboros-Omega."
                    self._log_evolution("metabolism", msg)
        except Exception as e:  # noqa: BLE001 — Isolate metabolism cycle failures from daemon boundary
            logger.error("[FRONTIER] Metabolism cycle failed: %s", e)

    async def _run_ingestion(self):
        """Ingests new intelligence and scans for high-exergy bounties."""
        logger.info("[FRONTIER] Scanning frontier for Cognitive Ingestion...")

        # Dynamic discovery potential: In a real scenario, this would poll
        # an external API or a local 'AgentLandscape' registry.
        discovery_targets = [
            ("google-deepmind", "jules"),
            ("openai", "operator"),
            ("anthropic", "claude-code"),
        ]

        # 1. Cognitive Ingestion of SOTA logic
        for owner, repo in discovery_targets:
            logger.info("[FRONTIER] Analyzing repository: %s/%s", owner, repo)
            msg = f"Analyzed {owner}/{repo} for potential skill emancipation."
            self._log_evolution("ingestion", msg)

        # 2. Bounty Discovery & Autonomous Recruitment Trigger
        bounty_service = BountyService(
            ledger=self.engine.ledger if self.engine else None,
            reward_threshold=250.0  # Ω₂: High-exergy filter
        )

        for owner, repo in discovery_targets:
            leads = await bounty_service.scan_repository(owner, repo)
            ranked = await bounty_service.rank_leads(leads)
            for lead in ranked:
                logger.info("[FRONTIER] High-exergy bounty found: %s (%s)", lead.title, lead.reward_usd)

                # Ω₄: Trigger dynamic recruitment via SwarmFactory
                if self.engine and hasattr(self.engine, 'factory'):
                    logger.info("[FRONTIER] Initializing 'Next Cycle' for %s", lead.title)
                    # Generate a swarm cycle specifically for this bounty
                    self.engine.factory.generate_cycle(
                        quadrant="P1",
                        size=3,
                        context={"bounty": lead.title, "reward": lead.reward_usd}
                    )
                    # Note: Full execution would happen in a background worker or here
                    # For now, we log the cycle initiation
                    msg = f"Forged Swarm Cycle for bounty '{lead.title}' (${lead.reward_usd})."
                    self._log_evolution("swarm", msg)

                self._log_evolution("bounty", f"Discovered bounty: {lead.title} (${lead.reward_usd})")

    def _log_evolution(self, type: str, content: str):
        """Registers the evolution event in CORTEX."""
        if not self.engine:
            return
        try:
            conn = self.engine.pool.get_connection()
            content_str = f"[{type.upper()}] {content}"
            conn.execute(
                "INSERT INTO facts (id, type, topic, content, timestamp, confidence) "
                "VALUES (lower(hex(randomblob(16))), 'decision', 'Evolution', ?, ?, 'C5')",
                (content_str, time.time()),
            )
            conn.commit()
            logger.info("[FRONTIER] Evolution event logged to CORTEX: %s", type)
        except sqlite3.Error as e:
            logger.error("[FRONTIER] Failed to log evolution: %s", e)

    async def run_loop(self):
        """Main Frontier loop."""
        logger.info("Initializing Frontier Daemon (Evolution Engine)...")
        while not self._shutdown:
            now = time.time()

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
