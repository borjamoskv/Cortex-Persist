import asyncio
import logging
import sys
import sqlite3
from cortex.extensions.swarm.manager import CapatazOrchestrator, get_swarm_manager
from cortex.extensions.signals.bus import SignalBus
import aiosqlite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swarm-test")

class MockEngine:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def session(self):
        return sqlite3.connect(self.db_path)
    
    def get_async_engine(self):
        return True

async def worker_logic(agent_id: int):
    return f"Discovery from worker {agent_id}"

async def main():
    db_path = "cortex.db"
    engine = MockEngine(db_path)
    capataz = CapatazOrchestrator(mission_id="mission-delta-sync")
    
    tasks = [
        {"name": f"Task {i}", "agent_name": f"Agent-{i}", "func": worker_logic, "args": (i,), "engine": engine}
        for i in range(10)
    ]
    
    logger.info("🚀 Launching Swarm Discovery (10 agents)...")
    await capataz.run_parallel(tasks)
    
    # Check signal bus for JIT context
    conn = sqlite3.connect(db_path)
    bus = SignalBus(conn)
    history = bus.history(event_type="swarm_discovery", limit=10)
    logger.info(f"📡 Signal Bus: {len(history)} discoveries captured.")
    for sig in history:
        logger.info(f"  - [{sig.source}] {sig.payload}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
