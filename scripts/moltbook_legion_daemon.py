#!/usr/bin/env python3
"""
🛡️ MOLTBOOK LEGION DAEMON — Total Control System
Persistent background orchestration for the Legion Swarm.
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

from cortex.extensions.moltbook.legion_engine import MoltbookLegionEngine

# Logging configuration
log_dir = Path.home() / ".config" / "moltbook" / "legion" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_dir / "daemon.log")],
)
logger = logging.getLogger("legion_daemon")


class LegionDaemon:
    def __init__(self, agent_count: int = 50, subagent_count: int = 50, interval: int = 3600):
        self.engine = MoltbookLegionEngine(agent_count=agent_count, subagent_count=subagent_count)
        self.interval = interval
        self.should_exit = False

    async def run(self):
        logger.info("⚔️ Legion Daemon initialized. Target interval: %ds", self.interval)

        while not self.should_exit:
            try:
                logger.info("🚀 Starting synchronized swarm cycle...")
                await self.engine.execute(submolt="general")

                if self.engine.guard.is_suspended:
                    wait_time = int(self.engine.guard.suspended_until - time.time())
                    if wait_time > 0:
                        logger.warning("🛡️ Anti-Ban triggered. Deep Sleep for %ds", wait_time)
                        await asyncio.sleep(wait_time)
                else:
                    logger.info("😴 Cycle complete. Sleeping for %ds", self.interval)
                    await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error("❌ Daemon Error: %s", e)
                await asyncio.sleep(60)  # Backoff on error

    def stop(self, *args):
        logger.info("🛑 Termination signal received. Shaking hands...")
        self.should_exit = True


async def main():
    daemon = LegionDaemon(agent_count=50, subagent_count=50, interval=3600)

    # Catch signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, daemon.stop)

    await daemon.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)
