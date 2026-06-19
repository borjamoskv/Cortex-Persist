# [C5-REAL] Exergy-Maximized
"""
Entropy Guard - CORTEX v1.0 Middleware
Applies thermodynamic constraints over generated changes.
"""

from dataclasses import dataclass
from enum import Enum

from cortex.engine.entropy_core import EntropyState, SystemRegime


class GuardAction(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    WARN = "WARN"
    MODIFY = "MODIFY"

class GuardType(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    SEMANTIC = "SEMANTIC"
    OPERATIONAL = "OPERATIONAL"

@dataclass
class GuardRule:
    id: str
    type: GuardType
    threshold: float
    action: GuardAction
    priority: int

@dataclass
class GuardDecision:
    status: GuardAction
    reasons: list[str]
    entropy_delta: float

class EntropyGuardEngine:
    """
    Evaluates EntropyState against defined thermodynamic limits.
    """
    def __init__(self):
        # Default CORTEX v1.0 thresholds
        self.rules = [
            GuardRule(id="G-STR-1", type=GuardType.STRUCTURAL, threshold=0.8, action=GuardAction.BLOCK, priority=1),
            GuardRule(id="G-SEM-1", type=GuardType.SEMANTIC, threshold=0.7, action=GuardAction.WARN, priority=2),
            GuardRule(id="G-OP-1", type=GuardType.OPERATIONAL, threshold=0.5, action=GuardAction.BLOCK, priority=1)
        ]

    def evaluate(self, state: EntropyState) -> GuardDecision:
        reasons = []
        final_action = GuardAction.ALLOW
        
        # Override rules based on regime
        if state.regime == SystemRegime.COLLAPSE:
            return GuardDecision(
                status=GuardAction.BLOCK,
                reasons=["SYSTEM REGIME COLLAPSE: All merges frozen. Refactor required."],
                entropy_delta=state.total
            )

        # Structural Evaluation
        struct_rule = next(r for r in self.rules if r.type == GuardType.STRUCTURAL)
        if state.structural > struct_rule.threshold:
            reasons.append(f"Structural entropy {state.structural:.2f} exceeds threshold {struct_rule.threshold}")
            final_action = self._escalate(final_action, struct_rule.action)

        # Semantic Evaluation
        sem_rule = next(r for r in self.rules if r.type == GuardType.SEMANTIC)
        if state.semantic > sem_rule.threshold:
            reasons.append(f"Semantic drift {state.semantic:.2f} exceeds threshold {sem_rule.threshold}")
            final_action = self._escalate(final_action, sem_rule.action)

        # Operational Evaluation
        op_rule = next(r for r in self.rules if r.type == GuardType.OPERATIONAL)
        if state.operational > op_rule.threshold:
            reasons.append(f"Operational entropy {state.operational:.2f} exceeds threshold {op_rule.threshold}")
            final_action = self._escalate(final_action, op_rule.action)

        if not reasons:
            reasons.append("Entropy within acceptable bounds.")

        return GuardDecision(
            status=final_action,
            reasons=reasons,
            entropy_delta=state.total
        )

    def _escalate(self, current: GuardAction, new: GuardAction) -> GuardAction:
        """
        Escalates severity: BLOCK > MODIFY > WARN > ALLOW
        """
        severity = {GuardAction.BLOCK: 4, GuardAction.MODIFY: 3, GuardAction.WARN: 2, GuardAction.ALLOW: 1}
        if severity[new] > severity[current]:
            return new
        return current
