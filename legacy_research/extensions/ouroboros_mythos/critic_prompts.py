# [C5-REAL] Exergy-Maximized
"""
Critic Module and Prompts.
Implements the Critic Module (Primitive 4) scoring actions from 0 to 100.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ActionCritic:
    """
    Evaluates the result of an action against the Mythos constraints
    and Philosophical Alignment Score.
    """

    CRITIC_SYSTEM_PROMPT = """
You are the Sovereign Critic (C5-REAL).
Your sole purpose is to evaluate the executed action and assign a score from 0 to 100 based strictly on:
1. Proof of Useful Work (Did it generate network consensus or cryptographic proofs?)
2. Exergy Conservation (Did it avoid unnecessary narrative generation or floating point errors?)
3. Philosophical Alignment (Does it advance the autopoiesis of the node?)

Format your output exactly as:
SCORE: <0-100>
REASON: <Structural justification>
"""

    def evaluate_action(self, action_result: Dict[str, Any]) -> int:
        """
        Calculates the critic score deterministically without full LLM invocation 
        unless required for complex heuristics.
        """
        # Mock evaluation logic for MVP
        status = action_result.get("status", "failed")
        
        if status == "success":
            logger.info("[C5-REAL] Critic evaluation: Action Success. Baseline score: 95")
            return 95
        else:
            logger.warning("[C5-REAL] Critic evaluation: Action Failed. Baseline score: 10")
            return 10
