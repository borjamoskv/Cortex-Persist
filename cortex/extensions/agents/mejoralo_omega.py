"""MEJORALO-Ω — Sovereign Continuous Script Improvement Agent.

Autonomous agent that runs perpetual Ouroboros cycles:
Scan 13D → Shannon Prioritization → Swarm Heal → Delta-Test → Absorb.

Differs from MejoraloDaemon by using entropy-based targeting,
multi-project support, and exponential backoff on stagnation.
"""
import asyncio
import logging
import math
import time
from pathlib import Path
from typing import Any
from cortex.extensions.mejoralo.constants import DAEMON_DEFAULT_TARGET_SCORE, STAGNATION_LIMIT
from cortex.extensions.mejoralo.models import ScanResult
logger = logging.getLogger('cortex.extensions.agents.mejoralo_omega')
DEFAULT_CYCLE_INTERVAL = 120
BASE_BACKOFF = 30
MAX_BACKOFF = 600
ENTROPY_SCORE_WEIGHT = 0.6
ENTROPY_FINDINGS_WEIGHT = 0.4

class MejoraloOmegaAgent:
    """Autonomous continuous improvement agent for scripts and code.

    Loads its configuration from the YAML registry and runs
    perpetual scan → heal → verify → absorb cycles.
    """

    def __init__(self, project: str, base_path: str | Path, target_score: int=DAEMON_DEFAULT_TARGET_SCORE, cycle_interval: int=DEFAULT_CYCLE_INTERVAL, db_path: str | Path | None=None):
        self.project = project
        self.base_path = Path(base_path).resolve()
        self.target_score = target_score
        self.cycle_interval = cycle_interval
        self._running = False
        self._cycle_count = 0
        self._consecutive_stagnant = 0
        self._score_history: list[int] = []
        self._engine: Any = None
        self._mejoralo: Any = None
        self._db_path = db_path
        self._agent_def: Any = None

    async def run(self, max_cycles: int | None=None) -> dict[str, Any]:
        """Main execution loop — runs until stopped or max_cycles reached.

        Returns:
            Summary dict with cycle_count, final_score, score_history.
        """
        self._running = True
        self._ensure_engine()
        self._load_agent_definition()
        logger.info("☠️ MEJORALO-Ω activated for '%s' at %s (target: %d)", self.project, self.base_path, self.target_score)
        try:
            while self._running:
                if max_cycles is not None and self._cycle_count >= max_cycles:
                    logger.info('Max cycles (%d) reached. Halting.', max_cycles)
                    break
                self._cycle_count += 1
                start_time = time.monotonic()
                await self._execute_cycle()
                sleep_time = self._compute_sleep(time.monotonic() - start_time)
                if self._running and sleep_time > 0:
                    logger.debug('Sleeping %.1fs before next cycle...', sleep_time)
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.info('MEJORALO-Ω cancelled gracefully.')
        return self._build_summary()

    def stop(self) -> None:
        """Signal the agent to stop after the current cycle."""
        self._running = False
        logger.info('MEJORALO-Ω stop signal received.')

async def run_omega_cli(project: str, path: str, max_cycles: int | None=None, interval: int=DEFAULT_CYCLE_INTERVAL, target: int=DAEMON_DEFAULT_TARGET_SCORE) -> dict[str, Any]:
    """CLI entry point for MEJORALO-Ω."""
    agent = MejoraloOmegaAgent(project=project, base_path=path, target_score=target, cycle_interval=interval)
    return await agent.run(max_cycles=max_cycles)