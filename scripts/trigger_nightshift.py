import asyncio

from cortex.cli.common import get_engine
from cortex.swarm.nightshift_daemon import NightShiftCrystalDaemon


async def main():
    engine = get_engine()
    daemon = NightShiftCrystalDaemon(cortex_db=engine, max_crystals=5)
    print("Starting NightShift cycle...")
    report = await daemon.run_cycle()
    print("NightShift Report:")
    for k, v in report.items():
        print(f"{k}: {v}")
    if report.get("consolidation"):
        print("\nConsolidation phase:")
        for k, v in report["consolidation"].items():
            print(f"{k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
