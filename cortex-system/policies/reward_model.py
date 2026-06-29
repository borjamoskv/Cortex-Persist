"""
C5-REAL: Reward Model & Reinforcement Cycle
Author: Borja Moskv / borjamoskv
"""
from typing import Dict, Any
MUTATION_RATE = 0.05
ORIGINALITY_THRESHOLD = 0.34
DISTRIBUTION_THRESHOLD = 0.26

def reinforcement_cycle(metric: Dict[str, Any], decision: str) -> str:
    """
    Evaluates metric yields to determine the next evolution/adaptation step.
    """
    originality_ratio = metric.get('originality_ratio', 1.0)
    distribution_yield = metric.get('distribution_yield', 1.0)
    if originality_ratio < ORIGINALITY_THRESHOLD:
        return 'force_swarm_mode'
    if distribution_yield < DISTRIBUTION_THRESHOLD:
        return 'inject_attention_pressure'
    if decision == 'default':
        return 'trigger_rupture'
    return 'stable'