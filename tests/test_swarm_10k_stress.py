# [C5-REAL] Exergy-Maximized
import asyncio
import shutil
import time
from pathlib import Path

from cortex.engine.swarm.swarm_10k import SwarmCommander


async def run_10k_stress():
    """Execute 10k agents stress test with parallel dispatch."""
    print("🚀 INITIALIZING LEGION-10k STRESS TEST (Zero-Noise Mandate)")

    # Path for test shards
    test_bus_dir = Path("/tmp/cortex_10k_stress")
    if test_bus_dir.exists():
        shutil.rmtree(test_bus_dir)
    test_bus_dir.mkdir()

    commander = SwarmCommander(bus_path=test_bus_dir)
    import sys

    print(f"DEBUG: SwarmCommander module: {sys.modules['cortex.engine.swarm.swarm_10k'].__file__}")
    print(f"DEBUG: SwarmCommander class: {SwarmCommander}")
    await commander.initialize()

    print(f"📡 Bus initialized with {commander.bus.num_shards} shards.")

    tasks = []
    # Create 10,000 tasks across 10 regions (Legions)
    for i in range(10000):
        domain = f"domain_{i % 10}"
        tasks.append({"id": i, "domain": domain, "payload": "stress_test_v6"})

    print("🌪️ Dispatching 10,000 tasks in parallel...")

    start_time = time.perf_counter()
    await commander.execute_global_dispatch(tasks, parallel=True)
    total_time = time.perf_counter() - start_time

    print(f"✅ Dispatch complete in {total_time:.4f}s")
    print(f"📊 Average dispatch latency: {(total_time / 10000) * 1000:.4f}ms per agent")

    report = await commander.get_density_report()
    print(f"📈 Density Report: {report}")

    # Verify 10,000 agents
    if report["agents"] != 10000:
        print(f"❌ ERROR: Expected 10,000 agents, found {report['agents']}")
    else:
        print("💎 GRAVITY-WELL STABILITY CONFIRMED: 10k agents crystallized.")

    print(f"Legions at teardown: {len(commander.legions)}")
    await commander.consolidate_and_annihilate()
    if test_bus_dir.exists():
        shutil.rmtree(test_bus_dir)


if __name__ == "__main__":
    try:
        asyncio.run(run_10k_stress())
    except Exception as e:
        import traceback

        print(f"❌ CRITICAL EXCEPTION IN MAIN: {e}")
        traceback.print_exc()
