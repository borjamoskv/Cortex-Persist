#!/usr/bin/env python3
"""
CORTEX v4.0 — God Mode Orchestrator (orchestrator.py)
Implements: /mejoralo --swarm --perpetual

Loop of excessive improvement using 520 Swarm Agents.
"""

import logging
import sys
import time

from cortex.config import DEFAULT_DB_PATH
from cortex.engine import CortexEngine
from cortex.launchpad import MissionOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [ORCHESTRATOR] - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("orchestrator")


def main():
    logger.info("🐉 INITIALIZING GOD MODE ORCHESTRATOR [520 AGENTS]")
    logger.info("Connecting to Cortex: %s", DEFAULT_DB_PATH)

    db_path = str(DEFAULT_DB_PATH)

    iteration = 1

    try:
        while True:
            logger.info("\n🌀 STARTING WAVE %s (TURBO MODE)", iteration)

            # Re-instantiate engine per loop to ensure fresh connection/avoid locks
            engine = CortexEngine(db_path=db_path)
            orchestrator = MissionOrchestrator(engine)

            # Define the mission for the swarm
            # We want to improve everything recursively
            mission_goal = (
                "MEJORAlo God Mode: Analyze codebase, identify entropy/debt, "
                "and execute high-impact refactors. Priority: Reliability, Speed, Aesthetics. "
                "Focus on test coverage and eliminating dead code."
            )

            try:
                logger.info("Launching Swarm Wave %s with 520 agents...", iteration)
                result = orchestrator.launch(
                    project="cortex",
                    goal=mission_goal,
                    formation="GOD_MODE",  # Custom formation for 520 agents
                    agents=520,  # The user request
                    context=f"Iteration: {iteration}, Mode: Turbo, Goal: Self-Improvement",
                )

                status = result.get("status")
                logger.info("Wave %s Complete. Status: %s", iteration, status)

                if status == "success":
                    logger.info("Result ID: %s", result.get('result_id'))
                    # In Turbo mode, we don't wait long.
                    logger.info("Cooling down for 2s (Turbo)...")
                    time.sleep(2)
                else:
                    logger.warning("Wave failed. Error: %s", result.get('error'))
                    logger.info("Retrying in 5s...")
                    time.sleep(5)

            except Exception as e:
                logger.error("Orchestration error: %s", e)
                time.sleep(10)
            finally:
                engine.close()

            iteration += 1

    except KeyboardInterrupt:
        logger.info("\n🛑 ORCHESTRATOR STOPPED BY USER")
        sys.exit(0)


if __name__ == "__main__":
    main()
