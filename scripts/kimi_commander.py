import asyncio
import argparse
import logging
from specialist_router import SpecialistRouter
from sandbox import SwarmSandbox


class KimiCommander:
    """The Supreme Orchestrator for the kimi-swarm-1 (Ω₁/Ω₃/Ω₅)."""

    def __init__(self):
        self.router = SpecialistRouter()
        self.sandbox = SwarmSandbox()
        self.logger = logging.getLogger("cortex.kimi.commander")

    async def execute_mission(self, mission: str, dry_run: bool = False):
        """Orchestrates the strategic split, competition, and consensus of the swarm."""
        self.logger.info(f"🚀 Mission Received: {mission}")

        # Phase 1: Strategic Split
        specialists = self.router.route_mission(mission)
        self.logger.info(f"🐝 Specialists Activated: {[s['id'] for s in specialists]}")

        # Phase 2 & 3: Sandbox Competition
        result = await self.sandbox.execute_competition(mission, specialists)

        if dry_run:
            self.logger.info("🛠️ Running in DRY-RUN mode (Ω₃ Simulation).")
            print("\n[SANDBOX CONSENSUS REPORT]")
            for p in result["proposals"]:
                print(f"- {p['specialist']}: {p['proposal']}")

            # Phase 4: LoreKeeper Persistence (Simulation)
            if any(s["id"] == "LoreKeeper" for s in specialists):
                print("\n[LOREKEEPER PERSISTENCE (Ω₁)]")
                msg = "Fact stored: Memory of graph-analysis findings successfully registered."
                print(msg)
            return result

        # Phase 5: Production Execution
        self.logger.warning("🔥 Production Mode requires active LLM API Keys and CORTEX write.")
        return {"status": "AWAITING_PRODUCTION_KEY"}


async def main():
    desc = "kimi-swarm-1 Commander"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("--mission", type=str, required=True, help="Task")
    parser.add_argument("--dry-run", action="store_true", help="Simulate")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    commander = KimiCommander()
    await commander.execute_mission(args.mission, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
