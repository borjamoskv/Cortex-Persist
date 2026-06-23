# [C5-REAL] Exergy-Maximized
"""
Decision Engine - CORTEX v1.0 Middleware
Resolves conflicts between LLM Intent, Guard Constraints, and System Entropy.
"""

import logging
from dataclasses import dataclass

from babylon60.engine.entropy_core import EntropyState, SystemRegime
from babylon60.guards.entropy_guard import GuardAction, GuardDecision

logger = logging.getLogger(__name__)

@dataclass
class PolicyResolution:
    action: GuardAction
    feedback: str
    suggested_rewrite: bool = False

class DecisionEngine:
    """
    Policy Layer that translates Guard outputs into actionable lifecycle decisions.
    """
    
    def resolve(self, entropy_state: EntropyState, guard_decision: GuardDecision) -> PolicyResolution:
        """
        D = f(LLM_output, entropy_state, guard_results)
        """
        if entropy_state.regime == SystemRegime.COLLAPSE:
            return PolicyResolution(
                action=GuardAction.BLOCK,
                feedback="SYSTEM COLLAPSE IMMINENT. Entropy overload. Force rollback or freeze writes.",
                suggested_rewrite=False
            )
            
        if guard_decision.status == GuardAction.ALLOW:
            return PolicyResolution(
                action=GuardAction.ALLOW,
                feedback="Entropy within acceptable bounds. Merging permitted.",
                suggested_rewrite=False
            )
            
        if guard_decision.status == GuardAction.WARN:
            # Check if semantic drift is the primary issue
            if any("Semantic" in reason for reason in guard_decision.reasons):
                return PolicyResolution(
                    action=GuardAction.WARN,
                    feedback="Semantic drift detected. Consider rewriting request to LLM to clarify intent.\nDetails: " + " | ".join(guard_decision.reasons),
                    suggested_rewrite=True
                )
            
        if guard_decision.status == GuardAction.BLOCK:
            return PolicyResolution(
                action=GuardAction.BLOCK,
                feedback="GUARD BLOCK triggered.\nDetails: " + " | ".join(guard_decision.reasons),
                suggested_rewrite=False
            )
            
        return PolicyResolution(
            action=guard_decision.status,
            feedback="Fallback resolution triggered.",
            suggested_rewrite=False
        )
