import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.swarm.reputation")

@dataclass
class AgentExergyProfile:
    agent_id: str
    success_count: int = 0
    failure_count: int = 0
    total_tokens: int = 0
    exergy_score: float = 100.0  # Base score
    
    def record_success(self, tokens: int):
        self.success_count += 1
        self.total_tokens += tokens
        # Exergy formula: success / log(tokens + 1)
        self.exergy_score += 10.0 / (tokens / 1000 + 1)

    def record_failure(self, tokens: int):
        self.failure_count += 1
        self.total_tokens += tokens
        self.exergy_score -= 20.0


class AgentReputationSystem:
    """
    Sovereign Reputation Guard (Ω-Exergy).
    Tracks efficiency and reliability across the swarm.
    """
    def __init__(self):
        self.profiles: dict[str, AgentExergyProfile] = {}

    def get_profile(self, agent_id: str) -> AgentExergyProfile:
        if agent_id not in self.profiles:
            self.profiles[agent_id] = AgentExergyProfile(agent_id=agent_id)
        return self.profiles[agent_id]

    def rank_agents(self, agent_ids: list[str]) -> list[str]:
        """Sort agents by exergy score (highest first)."""
        profiles = [self.get_profile(aid) for aid in agent_ids]
        sorted_profiles = sorted(profiles, key=lambda p: p.exergy_score, reverse=True)
        return [p.agent_id for p in sorted_profiles]
