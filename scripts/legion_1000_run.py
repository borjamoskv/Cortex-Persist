import asyncio
import time
from pathlib import Path

from cortex.engine.swarm_10k import SwarmCommander


async def run_dispatch():
    bus_path = Path("./cortex_swarm_1000_bus")
    commander = SwarmCommander(bus_path=bus_path)
    await commander.initialize()
    
    # 1000 agent tasks
    tasks = [{"domain": "exergy", "id": i} for i in range(1000)]
    
    print("🔱 Deploying Swarm: LEGION-1000 (Exergy Domain)")
    t0 = time.perf_counter()
    async with commander.strike_mode("exergy"):
        await commander.execute_global_dispatch(tasks)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    report = await commander.get_density_report()
    
    print("\n[DISPATCH TELEMETRY]")
    print(f"Total Agents: {report['agents']}")
    print(f"Centurions Created: {report['centurions']}")
    print(f"Legions Created: {report['legions']}")
    print(f"Wall-Clock Time: {elapsed_ms:.2f} ms")
    print(f"Throughput Rate: {report['agents'] / (elapsed_ms / 1000):.2f} agents/sec")
    
    await commander.consolidate_and_annihilate()
    print("\nConsolidated and annihilated successfully.")

if __name__ == "__main__":
    asyncio.run(run_dispatch())
