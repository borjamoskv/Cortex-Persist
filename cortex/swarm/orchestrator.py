import asyncio
import logging
from typing import Any

from cortex.engine.ledger import SovereignLedger

from .discovery import SkillRegistry
from .factory import SwarmFactory
from .manager import SwarmManager
from .partitioner import SwarmEnclave, SwarmPartitioner

logger = logging.getLogger("cortex.swarm.orchestrator")


class MasterOrchestrator:
    """
    Ω-Orchestrator: The Sovereign High Command.
    Orchestrates multiple SwarmManagers (Enclaves) and a SwarmFactory
    under a global MasterLedger.
    """

    def __init__(self, ledger: SovereignLedger | None = None) -> None:
        self.ledger = ledger
        self.enclaves: dict[SwarmEnclave, SwarmManager] = {
            enclave: SwarmManager(ledger=ledger)
            for enclave in SwarmEnclave
            if enclave != SwarmEnclave.GOVERNANCE
        }
        self.partitioner = SwarmPartitioner()
        self.registry = SkillRegistry()
        
        # We associate the factory with the EXECUTION enclave by default
        execution_manager = self.enclaves[SwarmEnclave.EXECUTION]
        execution_manager.registry = self.registry
        self.factory = SwarmFactory(execution_manager)
        
        self.global_context: dict[str, Any] = {}

    async def execute_global(self, complex_task: str) -> dict[str, Any]:
        """
        Divide and Conquer:
        1. Shard task into Enclaves.
        2. Dispatch parallel sub-swarms.
        3. Join results with dependency resolution.
        """
        logger.info("MasterOrchestrator: Executing global plan: '%s'...", complex_task[:50])
        shards = await self.partitioner.shard_complex_task(complex_task)
        results = {}
        dispatch_tasks = []

        for enclave, sub_tasks in shards.items():
            if not sub_tasks:
                continue

            manager = self.enclaves.get(enclave)
            if manager:
                for sub_t in sub_tasks:
                    # Parallel dispatch across sub-swarms
                    dispatch_tasks.append(self._dispatch_to_enclave(enclave, manager, sub_t))

        if dispatch_tasks:
            completed_results = await asyncio.gather(*dispatch_tasks)
            # Merge results into final synthesis
            for r in completed_results:
                results.update(r)

        return results

    async def _dispatch_to_enclave(
        self, enclave: SwarmEnclave, manager: SwarmManager, task: str
    ) -> dict[str, Any]:
        """Internal helper for enclave-specific execution."""
        logger.debug("Orchestrator: Dispatching to Enclave[%s]: %s", enclave.value, task)
        # Simplified result for protocol prototype
        return {f"{enclave.value}_result": f"Completed: {task}"}

    async def execute_swarm_100(self, global_goal: str) -> dict[str, Any]:
        """
        The Sovereign Swarm-100 Protocol.
        1. Massive Recruitment (100 Agents).
        2. Parallel Sharding via Enclaves.
        3. Crystallization & Ledger Audit.
        """
        logger.info("Orchestrator: Initiating SWARM-100 for goal: '%s'", str(global_goal)[:50])
        
        # 1. Recruitment
        squads = await self.factory.recruit_full_swarm()
        
        # 2. Execution (Parallel across all available agents)
        all_agents = squads["P0"] + squads["P1"] + squads["P2"]
        manager = self.enclaves[SwarmEnclave.EXECUTION] # Primary execution surface
        
        logger.info("Orchestrator: Dispatched goal to 100 agents.")
        responses = await manager.shard_task(all_agents, global_goal)
        
        # 3. Crystallization (Synthesis)
        success_count = len([r for r in responses if r.get("status") == "success"])
        total_exergy = sum(r.get("metadata", {}).get("exergy_yield", 0.0) for r in responses)
        
        synthesis = {
            "goal": global_goal,
            "agents_deployed": 100,
            "success_rate": f"{(success_count / 100) * 100:.1f}%",
            "total_exergy_extracted": total_exergy,
            "status": "crystallized" if success_count > 50 else "partial_success",
        }
        
        if self.ledger:
            self.ledger.record_transaction(
                project="swarm",
                action="swarm_100_crystallization",
                detail={
                    "goal": global_goal,
                    "metrics": synthesis,
                    "mechanical_justification": (
                        f"Synthesized output from 100 parallel actuators. "
                        f"Net exergy yield: {total_exergy}. "
                        f"Verified via SwarmManager reputation updates."
                    )
                }
            )
            
        return synthesis

    async def recruit_and_execute(self, quadrant: str, task: str) -> dict[str, Any]:
        """
        Higher-level flow: Recruit specialized agents for a task and execute it.
        """
        logger.info("Orchestrator: Recruiting for task '%s' in quadrant %s", task[:30], quadrant)
        squad = await self.factory.recruit_squad(quadrant, size=3)
        
        if not squad:
            return {"status": "error", "message": "No specialists recruited."}
            
        # Execution will be distributed via Enclaves in next iteration
        return {"status": "success", "squad_size": len(squad), "task": task}
