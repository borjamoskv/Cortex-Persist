import asyncio
import logging

from cortex.guards.exergy_guard import ExergyGuard

logger = logging.getLogger("cortex.swarm.guards.exergy")

class SwarmExergyGovernor:
    """
    Ω₂: The Swarm Thermodynamic Governor.
    
    Monitors exergy (work useful) across the swarm and throttles 
    agents that produce low-utility (decorative/redundant) output.
    """

    def __init__(self, threshold: float = 0.6):
        self._guard = ExergyGuard()
        self.threshold = threshold
        self.agent_scores: dict[str, float] = {}
        self.throttled_agents: set[str] = set()

    async def audit_agent_work(self, agent_id: str, content: str, fact_type: str = "knowledge"):
        """Audits the exergy of an agent's contribution and updates status."""
        try:
            score = self._guard.check_thermodynamic_yield(
                content=content,
                project_id="swarm_audit",
                fact_type=fact_type,
                taint="SWARM_CONTRIBUTION"
            )
            
            # Simple moving average for agent scoring
            prev_score = self.agent_scores.get(agent_id, 1.0)
            new_score = (prev_score * 0.7) + (score * 0.3)
            self.agent_scores[agent_id] = new_score

            if new_score < self.threshold:
                if agent_id not in self.throttled_agents:
                    logger.warning("Ω₂: Throttling agent %s due to low exergy yield (%.2f)", 
                                   agent_id, new_score)
                    self.throttled_agents.add(agent_id)
            else:
                if agent_id in self.throttled_agents:
                    logger.info("Ω₂: Reinstating agent %s (Exergy recovered to %.2f)", 
                                agent_id, new_score)
                    self.throttled_agents.remove(agent_id)

            return score
        except ValueError as e:
            logger.error("Ω₂ Violation: Agent %s rejected for 0% exergy contribution: %s", 
                         agent_id, e)
            self.agent_scores[agent_id] = 0.0
            self.throttled_agents.add(agent_id)
            raise

    def is_throttled(self, agent_id: str) -> bool:
        """Checks if an agent is currently under thermodynamic penalty."""
        return agent_id in self.throttled_agents

    async def wait_for_coolant(self, agent_id: str):
        """Forces an agent to wait if it's producing low exergy (entropy cooling)."""
        if self.is_throttled(agent_id):
            penalty_time = 5.0 * (1.0 - self.agent_scores.get(agent_id, 0.0))
            logger.debug("Ω₂: Cooling agent %s for %.2fs", agent_id, penalty_time)
            await asyncio.sleep(penalty_time)
