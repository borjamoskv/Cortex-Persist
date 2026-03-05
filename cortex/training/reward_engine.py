from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.training.collector import Trajectory

logger = logging.getLogger("cortex.training.reward")


class RewardEngine:
    """
    Assigns rewards to trajectories based on various signals.
    Follows reinforcement learning principles with test-based rewards.
    """

    def __init__(self, use_tests: bool = True):
        self.use_tests = use_tests

    def calculate_reward(self, trajectory: Trajectory) -> float:
        """
        Calculates a reward score between -1.0 and 1.0.
        """
        reward = 0.0

        # 1. Base outcome reward
        if trajectory.outcome == "success":
            reward += 0.5
        elif trajectory.outcome == "failure":
            reward -= 0.5
        
        # 2. Efficiency penalty (fewer steps are better)
        # Small penalty per step to encourage conciseness
        step_penalty = len(trajectory.actions) * 0.01
        reward -= min(step_penalty, 0.1)

        # 3. Test-based verification (Primary Reward)
        if self.use_tests and trajectory.outcome == "success":
            # If the metadata indicates tests passed, we give a major boost
            if trajectory.metadata.get("tests_passed", False):
                reward += 0.5
            elif trajectory.metadata.get("tests_run", False):
                # Tests ran but maybe not all passed or outcome is success but tests failed?
                # Usually inconsistent, but we reward the attempt.
                reward += 0.1

        # 4. Sentiment / Quality signals
        # If the agent was 'confident' or in 'flow', it's a positive signal
        if trajectory.metadata.get("avg_confidence", 0) > 0.8:
            reward += 0.1

        # Clip reward to [-1, 1]
        return max(min(reward, 1.0), -1.0)
