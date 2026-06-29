"""
C5-REAL: Delegation Map Configuration
Author: Borja Moskv / borjamoskv
"""

from typing import Any

AGENT_ROLES = {
    "A": {
        "key": "generator_alpha",
        "role": "generator",
        "description": "Noise and raw creative ideation injector.",
        "config": {"temperature": 0.85, "mode": "chaos", "noise_ratio": 0.4}
    },
    "B": {
        "key": "critic_omega",
        "role": "critic",
        "description": "Adversarial quality inspector, pruning sub-par proposals.",
        "config": {"strictness": 0.90, "originality_target": 0.60}
    },
    "C": {
        "key": "assembler_prime",
        "role": "assembler",
        "description": "Structural compilation and aesthetic coherence merger.",
        "config": {"strategy": "seamless", "synthesis_threshold": 0.70}
    },
    "D": {
        "key": "distributor_delta",
        "role": "distributor",
        "description": "Formatting, public ledger packaging, and external relaying.",
        "config": {"format": "canonical", "encryption": True}
    }
}

class DelegationMap:
    @staticmethod
    def get_agent(agent_id: str) -> dict[str, Any]:
        """Returns agent configurations from mapping key (A, B, C, D)."""
        return AGENT_ROLES.get(agent_id, {})

    @staticmethod
    def get_all_agents() -> list[dict[str, Any]]:
        """Returns list of all active configurations in the swarm."""
        return list(AGENT_ROLES.values())
