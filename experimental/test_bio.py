import asyncio
import os
import aiosqlite
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from cortex.engine.decalcifier import SovereignDecalcifier
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.swarm.centauro_engine import CentauroEngine, Formation
from cortex.daemon.models import CORTEX_DB

async def test_bio_architecture():
    print("🧬 Testing Bio-Architecture (Vector 6)...")
    os.environ["CORTEX_NO_LLM"] = "1"
    os.environ["CORTEX_TEST_MODE"] = "1"
    
    # 1. Test Swarm Modulation
    engine = CentauroEngine()
    print("\n--- Test 1: Normal Swarm (No Adrenaline) ---")
    res1 = await engine.engage("Mission Alpha", formation=Formation.SIEGE)
    print(f"Formation used: {res1.get('formation')} | Agents: {res1.get('agents_used')}")
    
    print("\n--- Test 2: High Adrenaline Swarm ---")
    lvl = ENDOCRINE.pulse(HormoneType.ADRENALINE, 1.0, reason="Simulated Security Compromise")
    print(f"Adrenaline manually spiked to: {lvl}")
    res2 = await engine.engage("Mission Beta", formation=Formation.SIEGE)
    print(f"Formation used: {res2.get('formation')} | Agents: {res2.get('agents_used')}")
    
    # 2. Test Decalcifier Cycle
    print("\n--- Test 3: Sovereign Decalcifier (REM Cycle) ---")
    decalcifier = SovereignDecalcifier()
    
    async with aiosqlite.connect(CORTEX_DB, timeout=5.0) as conn:
        print("Starting decalcify_cycle...")
        result = await decalcifier.decalcify_cycle(conn)
        print(f"REM Result: {result}")
        print(f"Current Serotonin: {ENDOCRINE.get_level(HormoneType.SEROTONIN)}")

if __name__ == "__main__":
    asyncio.run(test_bio_architecture())
