# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from collections import Counter

from cortex.sica.meta_level import MetaJudgment


class AdaptiveRetry:
    """Dynamic retry budgets based on failure classification.

    Instead of fixed max_retries=3, adapt based on:
    - Meta-failures get more retries (strategy was mutated, worth trying again)
    - Object-failures with same error get fewer (likely systematic)
    - Constitutional aborts get zero retries
    - First-time failure types get extra budget (might be transient)
    """

    def __init__(self, base_budget: int = 3) -> None:
        self._base = base_budget
        self._seen_failure_classes: Counter[str] = Counter()

    def compute_budget(self, judgment: MetaJudgment) -> int:
        """Compute the retry budget for a given judgment."""
        if judgment.constitutional_verdict and judgment.constitutional_verdict.abort_needed:
            return 0  # No retries on constitutional abort

        fc = judgment.failure_class
        if fc is None:
            return self._base

        fc_key = fc.value
        self._seen_failure_classes[fc_key] += 1
        times_seen = self._seen_failure_classes[fc_key]

        if judgment.is_meta_failure:
            # Meta-failures: strategy was mutated, give it room
            budget = self._base + 2
            # But diminish if this failure class keeps recurring
            budget = max(1, budget - (times_seen // 3))
        else:
            # Object-failures: diminish faster for known patterns
            budget = max(1, self._base - (times_seen // 2))

        # First-time failure types get a bonus
        if times_seen == 1:
            budget += 1

        return min(budget, self._base + 3)  # Hard cap

    def reset_for_class(self, failure_class: str) -> None:
        """Reset the counter for a failure class (e.g., after a success)."""
        if failure_class in self._seen_failure_classes:
            del self._seen_failure_classes[failure_class]
