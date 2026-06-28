# [C4-SIM]
"""
Gamification AI (Dopamine Loop).

Optimizes dopamine loops via stochastic rewards mapped to student computational exergy expenditure.
Dynamically modulates Flow State difficulty by injecting/removing friction variables.
"""

import random


class FlowStateModulator:
    def __init__(self, target_latency_ms: int = 5000):
        self.target_latency_ms = target_latency_ms

    def calculate_friction_delta(self, observed_latency_ms: int) -> float:
        """
        Determine if the student is bored (latency too low) or frustrated (latency too high).
        Returns friction multiplier.
        """
        ratio = observed_latency_ms / max(1, self.target_latency_ms)

        if ratio < 0.5:
            # Too easy, increase friction
            return 1.2
        elif ratio > 1.5:
            # Too hard, decrease friction
            return 0.8
        else:
            # Flow state achieved
            return 1.0

    def generate_stochastic_reward(self, exergy_expenditure: float) -> dict:
        """
        Generates a stochastic reward based on exergy spent.
        Variable ratio reinforcement schedule.
        """
        base_probability = min(0.9, exergy_expenditure * 0.1)

        # Stochastic trigger
        reward_triggered = random.random() < base_probability

        if reward_triggered:
            reward_magnitude = random.choice(["minor", "moderate", "major", "jackpot"])
        else:
            reward_magnitude = "none"

        return {
            "epistemic_level": "C4-SIM",
            "reward_triggered": reward_triggered,
            "reward_magnitude": reward_magnitude,
            "exergy_spent": exergy_expenditure,
        }
