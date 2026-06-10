"""
NOUS Deterministic Judge.
Evaluates AST against a strict security policy.
Reality Level: C5-REAL
"""

from typing import List
from dataclasses import dataclass
from .parser import MigrationIntent, MigrationAction

@dataclass
class JudgeVerdict:
    approved: bool
    reason: str
    warnings: List[str]

class DeterministicJudge:
    """
    Blocks destructive or unverified axioms.
    The LLM output is tainted data until it passes this gate.
    """
    
    FORBIDDEN_ACTIONS = {"DROP_TABLE", "TRUNCATE_TABLE", "DELETE_ALL"}
    
    @classmethod
    def evaluate(cls, intent: MigrationIntent) -> JudgeVerdict:
        warnings = []
        for action in intent.actions:
            if action.action_type in cls.FORBIDDEN_ACTIONS:
                return JudgeVerdict(
                    approved=False,
                    reason=f"SECURITY VIOLATION: Action {action.action_type} is explicitly forbidden by the Deterministic Judge.",
                    warnings=warnings
                )
                
            if action.action_type == "DROP_COLUMN":
                warnings.append(f"WARNING: Dropping column from {action.table_name}. Data loss potential.")
                
            # Type and structural checks can go here
            if not action.table_name.isidentifier():
                return JudgeVerdict(
                    approved=False,
                    reason=f"SYNTAX VIOLATION: Table name '{action.table_name}' is not a valid SQL identifier.",
                    warnings=warnings
                )
                
        return JudgeVerdict(
            approved=True,
            reason="All actions passed deterministic structural and security checks.",
            warnings=warnings
        )
