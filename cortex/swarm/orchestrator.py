import asyncio
import logging
from typing import Any

from cortex.ledger import SovereignLedger
from cortex.utils.pulmones import PulmonesQueue

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
        self._fallback_queue = PulmonesQueue()

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
        """Dispatch task to the first available actuator in the enclave manager."""
        logger.debug("Orchestrator: Dispatching to Enclave[%s]: %s", enclave.value, task)
        available = await manager.list_available()
        if not available:
            # No pre-registered actuators — attempt autonomic resolution via registry
            skills = list(manager.registry.skills.keys())
            if skills:
                agent_id = skills[0]
                try:
                    await manager._resolve_actuator(agent_id)
                    available = [agent_id]
                except ValueError:
                    pass

        if not available:
            return {f"{enclave.value}_result": {"status": "skipped", "reason": "no_actuators"}}

        # Cap at 5 agents per enclave to prevent event-loop saturation
        responses = await manager.shard_task(available[:5], task)
        success = [r for r in responses if r.get("status") == "success"]
        return {
            f"{enclave.value}_result": {
                "status": "success" if success else "partial",
                "agents_used": len(responses),
                "success_count": len(success),
                "samples": [r.get("content", "")[:200] for r in success[:3]],
            }
        }

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
        # Pull exergy from the governor's live per-agent scores instead of
        # metadata that virtual agents never populate.
        governor = manager.exergy_governor
        total_exergy = sum(governor.agent_scores.values())

        synthesis = {
            "goal": global_goal,
            "agents_deployed": 100,
            "success_rate": f"{(success_count / 100) * 100:.1f}%",
            "total_exergy_extracted": total_exergy,
            "status": "crystallized" if success_count > 50 else "partial_success",
        }

        if self.ledger:
            await self.ledger.record_transaction(
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
        Recruits a squad then dispatches the task via the EXECUTION enclave.
        """
        logger.info(
            "Orchestrator: Recruiting for task '%s' in quadrant %s",
            str(task)[:30],
            quadrant,
        )
        squad = await self.factory.recruit_squad(quadrant, size=3)

        if not squad:
            return {"status": "error", "message": "No specialists recruited."}

        manager = self.enclaves[SwarmEnclave.EXECUTION]
        responses = await manager.shard_task(squad, task)
        success = [r for r in responses if r.get("status") == "success"]
        return {
            "status": "success" if success else "partial",
            "squad_size": len(squad),
            "success_count": len(success),
            "task": task,
        }
