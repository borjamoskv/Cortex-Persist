# [C5-REAL] Exergy-Maximized
"""
cat_id: swarm-10k-consolidate
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

from babylon60.swarm.swarm_10k import SwarmCommander

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSOLIDAR_SCRIPT = REPO_ROOT / "scripts" / "consolidar_cortex.sh"


async def run_consolidation():
    print("🔱 LEGIØN-10k ACTIVATED: 10,000-AGENT PROJECT CONSOLIDATION")
    print("Initializing Sovereign Shared Bus...")

    bus_path = Path("/tmp/swarm_10k_bus")
    bus_path.mkdir(parents=True, exist_ok=True)

    commander = SwarmCommander(bus_path=bus_path, tenant_id="borjamoskv")
    await commander.initialize()

    # Construct 10,000 parallel micro-tasks for code consolidation
    print("Constructing 10,000 agent tasks...")
    tasks = [
        {
            "domain": "consolidation",
            "agent_id": i,
            "complexity": 5,
            "task": "audit_and_consolidate",
        }
        for i in range(10_000)
    ]

    print("Beginning hyper-scale parallel dispatch (10,000 agents)...")
    t0 = time.perf_counter()
    async with commander.strike_mode("consolidation"):
        await commander.execute_global_dispatch(tasks)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"✓ 10,000-Agent Parallel Dispatch completed in {elapsed_ms:.2f}ms")

    # Retrieve density parameters
    report = await commander.get_density_report()
    print(f"Density Report: {report}")

    # Trigger underlying physical consolidation
    print("\nExecuting Physical Repository Consolidation (Sync + Singularity Purge)...")

    if not CONSOLIDAR_SCRIPT.exists():
        logger.error("❌ Consolidation script not found: %s", CONSOLIDAR_SCRIPT)
        print("❌ Physical consolidation script missing.")
    else:
        result = subprocess.run(
            ["bash", str(CONSOLIDAR_SCRIPT)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print("❌ Physical consolidation encountered an error.")
            logger.error("STDERR: %s", result.stderr[-500:] if result.stderr else "")
        else:
            print("✅ Physical consolidation completed.")
            if result.stdout:
                # Print last 5 lines of stdout for visibility
                for line in result.stdout.strip().splitlines()[-5:]:
                    print(f"  {line}")

    await commander.consolidate_and_annihilate()
    print("🔱 Swarm memory freed. Consolidation Complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run_consolidation())
    except KeyboardInterrupt:
        print("\n⚡ Consolidation interrupted by operator.")
        sys.exit(130)
