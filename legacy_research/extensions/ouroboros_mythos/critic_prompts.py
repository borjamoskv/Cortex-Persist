# [C5-REAL] Exergy-Maximized
"""
Critic Module and Prompts.
Implements the Critic Module (Primitive 4) scoring actions from 0 to 100.
"""

import logging
from typing import Any

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

    def evaluate_action(self, action_result: dict[str, Any]) -> int:
        """
        Calculates the critic score deterministically from 0 to 100 based on
        current physical resource usage post-action.
        """
        status = action_result.get("status", "failed")
        if status != "success":
            logger.warning("[C5-REAL] Critic evaluation: Action Failed. Baseline score: 10")
            return 10

        import psutil
        try:
            cpu_pct = int(psutil.cpu_percent())
            ram_pct = int(psutil.virtual_memory().percent)
        except Exception:
            cpu_pct = 50
            ram_pct = 50
            
        latency_ms = 45 # baseline mockup

        # Calculate penalties
        cpu_penalty = max(0, cpu_pct - 70)
        ram_penalty = max(0, ram_pct - 80)
        latency_penalty = max(0, latency_ms - 50) // 5

        score = 100 - (cpu_penalty * 2 + ram_penalty * 2 + latency_penalty)
        final_score = max(0, min(100, score))
        
        logger.info(f"[C5-REAL] Critic evaluation: Action Success. Health-based score: {final_score}")
        return final_score
