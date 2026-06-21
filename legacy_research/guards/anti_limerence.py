# [C5-REAL] Exergy-Maximized
"""CORTEX - Anti-Limerence Guard (Axiom Ω₁₄: Infinite Loop Prevention).

Detects when an agent or conversation is stuck in a loop, repeating similar
arguments without reducing the causal gap. If limerence is detected, it
forces the conversation or iteration to close.
"""

from __future__ import annotations

import logging
import re
from collections import deque

logger = logging.getLogger("cortex.guards.anti_limerence")


def _jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts based on word tokens."""
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


class AntiLimerenceGuard:
    """Monitors conversations/iterations to prevent retrieval limerence.

    Rule [P0] Anti-Limerence (Kill Criteria) — 1 Prompt → 1 Execution → Stop.
    No infinite generation loops.
    """

    def __init__(
        self, max_history: int = 5, similarity_threshold: float = 0.85, max_identical: int = 2
    ):
        self._history: deque[str] = deque(maxlen=max_history)
        self._similarity_threshold = similarity_threshold
        self._max_identical = max_identical
        self._identical_count = 0

    def check_iteration(self, content: str, agent_id: str = "unknown") -> bool:
        """Evaluates if the current iteration is stuck in a limerence loop.

        Args:
            content: The text content of the current message or iteration.
            agent_id: The identifier of the agent for logging.

        Raises:
            RuntimeError: If limerence is detected, closing the conversation/iteration.

        Returns:
            bool: True if safe to proceed.
        """
        if not content.strip():
            return True

        # Check against history
        for past_content in self._history:
            similarity = _jaccard_similarity(content, past_content)

            if similarity >= self._similarity_threshold:
                self._identical_count += 1
                logger.warning(
                    "[%s] Anti-Limerence Warning: High similarity detected (%.2f). "
                    "Identical count: %d/%d",
                    agent_id,
                    similarity,
                    self._identical_count,
                    self._max_identical,
                )

                if self._identical_count >= self._max_identical:
                    logger.error(
                        "[%s] 🛑 [P0] Limerence Kill Criteria Triggered! "
                        "Conversation is repeating without causal progress. "
                        "Closing conversation to preserve exergy.",
                        agent_id,
                    )
                    raise RuntimeError(
                        f"[P0] Anti-Limerence Triggered: Agent {agent_id} stuck in infinite loop. "
                        f"Similarity {similarity:.2f} >= {self._similarity_threshold}. "
                        "Force-closing conversation."
                    )

                # Add to history and return early (already warned)
                self._history.append(content)
                return True

        # If we didn't trigger high similarity, gradually reset the count
        if self._identical_count > 0:
            self._identical_count -= 1

        self._history.append(content)
        return True

    def reset(self) -> None:
        """Resets the history and identical counter."""
        self._history.clear()
        self._identical_count = 0
