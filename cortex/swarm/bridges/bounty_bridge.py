import logging
from typing import Any

from cortex.services.bounty_service import BountyService
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager

logger = logging.getLogger("cortex.swarm.bridges.bounty_bridge")


class BountySwarmBridge:
    """
    Kinetic Signal-Purification Bridge (Ω₂).
    Links BountyService discovery with SwarmFactory execution.
    """

    def __init__(
        self,
        bounty_service: BountyService,
        factory: SwarmFactory,
        manager: SwarmManager,
    ) -> None:
        self.bounty_service = bounty_service
        self.factory = factory
        self.manager = manager
        self.ledger = manager.ledger

    async def bridge_high_exergy_bounties(
        self, owner: str, repo: str, squad_size: int = 3
    ) -> dict[str, Any]:
        """
        Automated Kinetic Workflow:
        1. Scan for bounties.
        2. Rank by reward exergy.
        3. Recruit specialized squad.
        4. Distribute and execute.
        """
        logger.info("🛡️ BountyBridge: Activating Kinetic Bridge for %s/%s", owner, repo)

        # 1. Scan and Rank
        leads = await self.bounty_service.scan_repository(owner, repo)
        ranked = self.bounty_service.rank_leads(leads)

        if not ranked:
            logger.info("BountyBridge: No high-exergy leads found in %s/%s", owner, repo)
            return {"status": "idle", "leads_processed": 0}

        results = []
        for lead in ranked:
            # 2. Squad Recruitment (Ω₁₃)
            logger.info("BountyBridge: Recruiting squad for bounty #%d: %s", lead.number, lead.title)
            agent_ids = await self.factory.recruit_squad("frontline", size=squad_size)

            # 3. Task Distribution
            task_prompt = self.bounty_service.generate_claim_prompt(lead)
            
            # 4. Kinetic Execution (Ω₃)
            responses = await self.manager.shard_task(agent_ids, task_prompt)
            
            # 5. Ledger Record (Ω₉)
            if self.ledger:
                self.ledger.record_transaction(
                    project="swarm",
                    action="kinetic_bridge_activation",
                    detail={
                        "bounty_id": lead.number,
                        "repo": lead.repo,
                        "reward": lead.reward_usd,
                        "squad_size": len(agent_ids),
                        "agent_ids": agent_ids,
                        "mechanical_justification": (
                            f"Kinetic bridge triggered by high-exergy lead ({lead.reward_usd} "
                            "USD). Recruited specialists via SwarmFactory. "
                            "Task sharded with consensus verification. "
                            "Execution entropy reduced via autonomic sharding."
                        )
                    }
                )
            
            results.append({
                "bounty": lead.number,
                "agents": agent_ids,
                "responses": [r["status"] for r in responses]
            })

        return {
            "status": "kinetic_active",
            "leads_processed": len(ranked),
            "results": results
        }
