import json
import logging
from typing import Any

from cortex.engine.heuristic import HeuristicEngine
from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile

logger = logging.getLogger("cortex.engine.llm_heuristic")

class LLMHeuristicEngine(HeuristicEngine):
    """
    LLM-driven Heuristic Engine for ARC-AGI PUCT MCTS.
    Uses an LLM to predict prior probabilities of primitives based on grid state.
    """

    def __init__(self, manager: LLMManager | None = None):
        self.manager = manager or LLMManager()

    async def predict(
        self, state: dict[str, Any], available_actions: list[str]
    ) -> tuple[dict[str, float], float]:
        """
        Queries the LLM to get prior probabilities for available actions.
        """
        if not self.manager.available:
            logger.warning("LLM Manager not available, falling back to uniform priors.")
            p = {action: 1.0 / len(available_actions) for action in available_actions}
            return p, 0.0

        grid = state.get("grid")
        target = state.get("target")
        program_so_far = state.get("program", [])

        # Construct high-exergy prompt
        prompt = (
            f"Analyze the ARC-AGI transformation.\n"
            f"Input Grid: {grid}\n"
            f"Target Grid (Target): {target}\n"
            f"Current Program Path: {program_so_far}\n\n"
            f"Available primitives: {available_actions}\n\n"
            f"Task: Predict the probability distribution 'p' for the next best primitive "
            f"to apply.\n"
            f"Also provide a value estimate 'v' for the current state (-1.0 to 1.0).\n"
            f"'v' should be near 1.0 if the current program path is likely to lead to the target.\n"
            f"\nRespond STRICTLY with JSON:\n"
            f"{{\n  \"p\": {{ \"primitive_name\": float_probability, ... }},\n  \"v\": float_value\n}}"
        )
        try:
            response_text = await self.manager.complete(
                prompt=prompt,
                system="You are an ARC-AGI heuristic engine specialized in PeARL-like symbolic primitives.",
                intent=IntentProfile.CODE,
                temperature=0.1
            )

            if not response_text:
                raise ValueError("Empty LLM response")

            # Clean response text (remove markdown blocks if any)
            clean_json = response_text.strip()
            if "```" in clean_json:
                clean_json = clean_json.split("```")[1]
                if clean_json.startswith("json"):
                    clean_json = clean_json[4:]
            
            data = json.loads(clean_json.strip())
            
            p_raw = data.get("p", {})
            v = float(data.get("v", 0.0))

            # Filter and normalize p
            p: dict[str, float] = {}
            for k_raw, v_raw in p_raw.items():
                if k_raw in available_actions:
                    p[str(k_raw)] = float(v_raw)
            
            sum_p: float = sum(p.values())
            if sum_p == 0:
                p = {action: 1.0 / float(len(available_actions)) for action in available_actions}
            else:
                p = {k: v / sum_p for k, v in p.items()}
            
            # Ensure all available actions have at least epsilon probability
            epsilon: float = 0.01
            for action in available_actions:
                if action not in p or p[action] < epsilon:
                    p[action] = epsilon
            
            # Final re-normalization
            final_sum: float = sum(p.values())
            p = {k: v / final_sum for k, v in p.items()}

            return p, float(v)

        except Exception as e:
            logger.error(
                "LLMHeuristicEngine prediction failed: %s. Response was: %s",
                e,
                response_text if "response_text" in locals() else "None",
            )
            # Fallback to uniform
            return {a: 1.0 / len(available_actions) for a in available_actions}, 0.0
