import asyncio
import logging
import sqlite3
import sys
from cortex.extensions.swarm.manager import CapatazOrchestrator
from cortex.extensions.swarm.protocols import AgentRole
from cortex.extensions.signals.bus import SignalBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elder-test")

class MockEngine:
    def __init__(self, db_path):
        self.db_path = db_path
    def session(self):
        return sqlite3.connect(self.db_path)
    def get_async_engine(self):
        return True

async def worker_bad_proposal():
    return "Fix applied: HACK the core logic to skip validation."

async def main():
    db_path = "cortex.db"
    engine = MockEngine(db_path)
    capataz = CapatazOrchestrator(mission_id="mission-high-risk-test")
    
    # 🚩 Marcamos como High Risk tocando engine/models.py
    tasks = [
        {
            "name": "Update Core Models", 
            "agent_name": "Agent-Worker-1", 
            "func": worker_bad_proposal, 
            "role": AgentRole.WORKER,
            "args": (),
            "kwargs": {},
            "changed_files": ["cortex/engine/models.py"],
            "engine": engine
        }
    ]
    
    logger.info("🚀 Launching High-Risk Task (Expecting Rejection)...")
    results = await capataz.run_parallel(tasks)
    
    for res in results:
        if isinstance(res, Exception):
            logger.warning(f"✅ Rejection caught: {res}")

    # Verificar SignalBus para ver el Negative Knowledge del Elder
    conn = sqlite3.connect(db_path)
    bus = SignalBus(conn)
    history = bus.history(event_type="swarm_discovery", limit=5)
    found_elder = False
    for sig in history:
        # Payload is stored as a JSON string in SignalBus, let's look for rejection
        if "rejection" in str(sig.payload):
            logger.info("🧠 Negative Knowledge Captured in SignalBus")
            found_elder = True
            break
    if not found_elder:
        logger.error("❌ Negative Knowledge NOT found in SignalBus")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
