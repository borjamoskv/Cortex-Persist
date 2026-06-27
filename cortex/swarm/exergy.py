"""
[C5-REAL] Exergy Tokenomics & Staking Mechanism for OUROBOROS.
Manages agent exergy (vitality) inside the Byzantine Swarm.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgentWallet:
    agent_id: str
    balance: float
    staked: float = 0.0
    successful_commits: int = 0
    failed_commits: int = 0
    is_alive: bool = True


class ExergyBank:
    """
    Central Ledger for tracking the vitality (Exergy) of agents in the swarm.
    """

    INITIAL_EXERGY = 1000.0  # Tokens fiat (Virtual representation of API Cost limits)
    STAKE_REQUIRED_PER_PROPOSAL = 50.0
    REWARD_MULTIPLIER = 1.5

    def __init__(self):
        self.wallets: dict[str, AgentWallet] = {}

    def register_agent(self, agent_id: str) -> AgentWallet:
        if agent_id not in self.wallets:
            self.wallets[agent_id] = AgentWallet(agent_id=agent_id, balance=self.INITIAL_EXERGY)
        return self.wallets[agent_id]

    def stake(self, agent_id: str) -> bool:
        """
        Agent stakes Exergy to propose an AST mutation.
        Returns True if successful, False if bankrupt.
        """
        wallet = self.wallets.get(agent_id)
        if not wallet or not wallet.is_alive:
            return False

        if wallet.balance < self.STAKE_REQUIRED_PER_PROPOSAL:
            wallet.is_alive = False
            logger.warning(f"Agent {agent_id} BANKRUPT (Death by Exergy Depletion).")
            return False

        wallet.balance -= self.STAKE_REQUIRED_PER_PROPOSAL
        wallet.staked += self.STAKE_REQUIRED_PER_PROPOSAL
        return True

    def slash(self, agent_id: str) -> None:
        """
        Punish agent for a failed compilation, failed tests, or hallucinations.
        """
        wallet = self.wallets.get(agent_id)
        if wallet and wallet.staked >= self.STAKE_REQUIRED_PER_PROPOSAL:
            wallet.staked -= self.STAKE_REQUIRED_PER_PROPOSAL
            wallet.failed_commits += 1
            logger.info(
                f"Agent {agent_id} SLASHED (Lost {self.STAKE_REQUIRED_PER_PROPOSAL} exergy)."
            )

    def reward(self, agent_id: str) -> None:
        """
        Reward agent for a successful PoQ (Proof of Quality) mutation.
        """
        wallet = self.wallets.get(agent_id)
        if wallet and wallet.staked >= self.STAKE_REQUIRED_PER_PROPOSAL:
            wallet.staked -= self.STAKE_REQUIRED_PER_PROPOSAL
            reward = self.STAKE_REQUIRED_PER_PROPOSAL * self.REWARD_MULTIPLIER
            wallet.balance += reward
            wallet.successful_commits += 1
            logger.info(f"Agent {agent_id} REWARDED (+{reward} exergy).")

    def dissipate_agent(self, agent_id: str, registry) -> None:
        """
        Entropic Dissipation (Weaponized Forgetting).
        Bankrupts the agent and physically removes it from the Swarm Registry (Apoptosis).
        """
        wallet = self.wallets.get(agent_id)
        if wallet:
            wallet.is_alive = False
            wallet.balance = 0.0
            logger.warning(f"[C5-REAL] Agent {agent_id} DISSIPATED (Entropy Purge). Apoptosis executed.")
        
        if hasattr(registry, "_agents"):
            keys_to_remove = [k for k, v in registry._agents.items() if getattr(v, "agent_id", None) == agent_id]
            for k in keys_to_remove:
                del registry._agents[k]

    def get_state(self) -> dict[str, dict]:
        return {
            aid: {
                "balance": w.balance,
                "staked": w.staked,
                "alive": w.is_alive,
                "win_rate": w.successful_commits / max(1, w.successful_commits + w.failed_commits),
            }
            for aid, w in self.wallets.items()
        }
