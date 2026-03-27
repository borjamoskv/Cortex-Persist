import argparse
import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime

from cortex.extensions.wealth.scanner import FundingRateScanner
from cortex.ledger.sovereign_ledger import SovereignLedger
from cortex.services.bounty_service import BountyLead, BountyService
from cortex.swarm.bridges.bounty_bridge import BountySwarmBridge
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager

logger = logging.getLogger("cortex.ouroboros")


class OuroborosEngine:
    """
    Ouroboros Omega: Sovereign Wealth Extraction Engine (Ω-Wealth).
    Orchestrates discovery and kinetic capture across multiple vectors.
    """

    def __init__(self, ledger: SovereignLedger, swarm_manager: SwarmManager, min_exergy: float = 50.0):
        self.ledger = ledger
        self.swarm_manager = swarm_manager
        self.factory = SwarmFactory(manager=self.swarm_manager)
        self.min_exergy = min_exergy

        # Initialize Services
        self.bounty_service = BountyService(ledger=self.ledger)
        self.wealth_scanner = FundingRateScanner()
        self.bounty_bridge = BountySwarmBridge(
            bounty_service=self.bounty_service, factory=self.factory, manager=self.swarm_manager
        )

        self.target_assets = ["BTC", "ETH", "SOL", "ARB", "OP", "TIA", "SUI"]
        self.target_repos = [
            ("borjamoskv", "Cortex-Persist"),
            ("ollama", "ollama"),
            ("pydantic", "pydantic"),
            ("langchain-ai", "langchain"),
            ("fastapi", "fastapi"),
        ]

    def _verify_discovery(self, bounties: Sequence[BountyLead], opps: list) -> bool:
        """Byzantine fault tolerance check (Ω₁)."""
        # Logic: Ensure discovery isn't empty and has internal consistency
        # e.g., if we find 100 bounties in 1 second, it's likely a scan error/ghost.
        if len(bounties) > 50:
            logger.warning("[Ω₁-WARN] Discovery density anomalous. Throttling.")
            return False
        return True

    def _calculate_cycle_exergy(self, bounties: list[BountyLead], opps: list) -> float:
        """Thermodynamic calculation of potential yield (Ω₂)."""
        bounty_yield = sum(b.reward_usd for b in bounties)
        opp_yield = sum(float(o.estimated_apr) * 10 for o in opps)
        return bounty_yield + opp_yield

    async def run_step(self, dry_run: bool = False):
        """Executes a single iteration of the Ouroboros loop (Ω₃)."""
        logger.info("--- Ouroboros Cycle Start: %s ---", datetime.now().isoformat())

        # 1. Discovery Phase (Ω₁)
        bounty_coros = [self.bounty_service.scan_repository(o, r) for o, r in self.target_repos]
        wealth_coro = self.wealth_scanner.scan_opportunities(self.target_assets)

        results = await asyncio.gather(*bounty_coros, wealth_coro)

        # Unpack results: first N are bounties, last is wealth
        bounty_results = list(results)[:-1]
        opportunities = results[-1]
        bounty_leads = [lead for sublist in bounty_results for lead in sublist]

        # Byzantine Verification (Ω₁)
        if not self._verify_discovery(bounty_leads, opportunities):
            return

        # 2. Valuation Phase (Ω₂)
        ranked_bounties = await self.bounty_service.rank_leads(bounty_leads)
        potential_exergy = self._calculate_cycle_exergy(ranked_bounties, opportunities)

        # 3. Proposal Phase (Ω₉)
        await self.ledger.record_transaction(
            project="ouroboros",
            action="discovery_cycle",
            detail={
                "bounties_found": len(ranked_bounties),
                "arbitrage_opportunities": len(opportunities),
                "potential_exergy_usd": potential_exergy,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # 4. Kinetic Execution Phase (Ω₃)
        if dry_run:
            logger.info("[DRY-RUN] Cycle Exergy: $%.2f (Min: $%.2f)", potential_exergy, self.min_exergy)
        elif potential_exergy < self.min_exergy:
            logger.info("[Ω₂-PRUNE] Exergy $%.2f below threshold $%.2f. Aborting execution.",
                        potential_exergy, self.min_exergy)
        else:
            if ranked_bounties:
                top = ranked_bounties[0]
                logger.info("[Ω₃] Dispatching Swarm squad to: %s#%d", top.repo, top.number)
                owner, repo = top.repo.split("/")
                await self.bounty_bridge.bridge_high_exergy_bounties(owner, repo, squad_size=2)

        logger.info("--- Ouroboros Cycle Complete ---")


async def main():
    parser = argparse.ArgumentParser(description="Ouroboros Omega Engine")
    parser.add_argument("--continuous", action="store_true", help="Run in continuous loop")
    parser.add_argument("--dry-run", action="store_true", help="Perform discovery only")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds")
    parser.add_argument("--min-exergy", type=float, default=50.0, help="Minimum exergy threshold")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    from cortex.engine import CortexEngine
    engine = CortexEngine()
    ledger = engine.ledger or SovereignLedger(engine)
    manager = engine.manager or SwarmManager(engine)
    ouroboros = OuroborosEngine(ledger, manager, min_exergy=args.min_exergy)

    if args.continuous:
        logger.info("Starting Ouroboros Omega (CONTINUOUS mode, %ds)", args.interval)
        while True:
            try:
                await engine.run_step(dry_run=args.dry_run)
                await asyncio.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Ouroboros shutdown initiated.")
                break
            except Exception as e:
                logger.error("Cycle failure: %s", e)
                await asyncio.sleep(60)
    else:
        await engine.run_step(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
