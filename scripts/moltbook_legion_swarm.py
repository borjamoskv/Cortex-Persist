#!/usr/bin/env python3
"""
Moltbook Legion Swarm — Entry Script
Scale: 50x50 (100 Entities)
Specialty: Legion-Ω Collective Intelligence
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.extensions.moltbook.legion_engine import MoltbookLegionEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | 🛡️ LEGION-SWARM | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("legion_swarm")


async def main():
    logger.info("--- LEGION-Ω HYPER-SCALE DEPLOYMENT ---")
    logger.info("Target: 50 Agents (Posters) + 50 SubAgents (Commenters)")

    engine = MoltbookLegionEngine(agent_count=50, subagent_count=50)

    try:
        await engine.execute(submolt="general")
        logger.info("✅ Operation completed. Swarm achieved consensus dominance.")
    except Exception as e:
        logger.error("❌ Operation failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
