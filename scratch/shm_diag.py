import asyncio
import time
from multiprocessing import resource_tracker
from cortex.engine.swarm_10k import SwarmCommander


async def diag():
    import sys

    print("DEBUG: sys.path:", sys.path)
    print(
        "Pre-test tracking:",
        resource_tracker._resource_tracker._fd
        if hasattr(resource_tracker, "_resource_tracker")
        else "N/A",
    )

    commander = SwarmCommander(bus_path="/tmp/cortex_diag")
    await commander.initialize()

    # Spawn 10 centurions
    for i in range(10):
        legion = await commander.get_or_create_legion(f"diag_{i}")
        await legion.ensure_centurion()

    report = await commander.get_density_report()
    print(f"Created {report['centurions']} centurions")

    print("Executing annihilation...")
    await commander.consolidate_and_annihilate()

    print("Post-annihilation check...")
    # There is no public API to list tracked resources, but we can check if warnings appear at exit.


if __name__ == "__main__":
    asyncio.run(diag())
