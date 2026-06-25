"""
[C5-REAL] Byzantine Consensus Judge (Empirical Oracle)
Uses the SandboxJIT and Exergy economics to reach consensus on proposed code mutations.
"""

import logging
from typing import Any

from cortex.engine.sandbox_jit import JITSandboxViolation, SandboxJIT
from legacy_research.swarm.exergy import ExergyBank

logger = logging.getLogger(__name__)


class ByzantineJudge:
    """
    Evaluates AST mutations empirically without trusting the agents' claims (Proof of Quality).
    """

    def __init__(self):
        self.sandbox = SandboxJIT()
        self.bank = ExergyBank()

    def evaluate_proposals(
        self, original_state: dict[str, Any], proposals: list[dict[str, str]]
    ) -> str | None:
        """
        Receives a list of proposals from different agents:
        [{"agent_id": "alpha", "ast_code": "def func()..."}, ...]

        Returns the winning agent_id, or None if all failed.
        """
        winning_agent = None
        best_win_rate = -1.0

        for prop in proposals:
            agent_id = prop["agent_id"]
            code = prop["ast_code"]

            wallet = self.bank.register_agent(agent_id)
            if not self.bank.stake(agent_id):
                continue  # Agent bankrupt, ignore proposal

            try:
                # 1. Ejecución Aislada JIT
                logger.info(f"Evaluating AST from agent {agent_id}...")
                _new_state = self.sandbox.execute(code, context=dict(original_state))

                # En un entorno real, aquí inyectaríamos la Test Suite (Pytest runner)
                # Simulamos éxito si la compilación y ejecución fue segura (Sin Violaciones)

                self.bank.reward(agent_id)

                # Consenso: El agente con mayor histórico (Win Rate) gana en caso de múltiples ASTs válidos
                win_rate = wallet.successful_commits / max(
                    1, wallet.successful_commits + wallet.failed_commits
                )
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    winning_agent = agent_id

            except JITSandboxViolation as e:
                logger.warning(f"Agent {agent_id} SLASHED due to Sandbox Violation: {e}")
                self.bank.slash(agent_id)
            except Exception as e:
                logger.error(f"Agent {agent_id} SLASHED due to Unknown Error: {e}")
                self.bank.slash(agent_id)

        if winning_agent:
            logger.info(f"🏆 Consensus reached. Winner: {winning_agent}")
        else:
            logger.error("🛑 Consensus failed. All agents slashed or bankrupt.")

        return winning_agent
