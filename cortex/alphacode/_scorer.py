# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""AlphaCode — Solution Scorer.

Uses a secondary LLM pass to assess correctness probability
for each solution within its cluster. Enables selection of the
best representative per cluster.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from cortex.alphacode._models import (
    ClusterResult,
    Problem,
    ScoredSolution,
)

if TYPE_CHECKING:
    from cortex.llm.provider import LLMProvider

logger = logging.getLogger("cortex.alphacode.scorer")


_SCORING_SYSTEM = """\
You are a competitive programming judge. Evaluate the given solution's correctness.
Score from 0.0 (certainly wrong) to 1.0 (certainly correct).

Consider:
- Algorithmic correctness
- Edge case handling
- Time/space complexity vs constraints
- Code quality and readability

Respond with ONLY a JSON object: {"score": 0.X, "rationale": "brief reason"}"""

_SCORE_RE = re.compile(r'"score"\s*:\s*([0-9.]+)')


class Scorer:
    """Assign correctness scores to solutions using LLM evaluation."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        temperature: float = 0.1,
    ) -> None:
        self._llm = llm
        self._temperature = temperature

    async def score_clusters(
        self,
        clusters: list[ClusterResult],
        problem: Problem,
    ) -> list[ScoredSolution]:
        """Score the representative solution of each cluster."""
        scored: list[ScoredSolution] = []

        for cluster in clusters:
            sol = cluster.representative
            score, rationale = await self._score_single(sol.code, problem)

            scored.append(
                ScoredSolution(
                    solution=sol,
                    cluster_id=cluster.cluster_id,
                    score=score,
                    scoring_model=self._llm.model_name,
                    rationale=rationale,
                )
            )

        # Sort by score descending
        scored.sort(key=lambda s: s.score, reverse=True)
        logger.info(
            "Scored %d cluster representatives, top score: %.2f",
            len(scored),
            scored[0].score if scored else 0.0,
        )
        return scored

    async def _score_single(
        self,
        code: str,
        problem: Problem,
    ) -> tuple[float, str | None]:
        """Score a single solution. Returns (score, rationale)."""
        prompt = (
            f"## Problem: {problem.title}\n\n"
            f"{problem.statement}\n\n"
            f"## Solution to evaluate:\n```\n{code}\n```\n\n"
            "Evaluate this solution's correctness."
        )

        try:
            raw = await self._llm.complete(
                prompt=prompt,
                system=_SCORING_SYSTEM,
                temperature=self._temperature,
                max_tokens=256,
            )

            match = _SCORE_RE.search(raw)
            if match:
                score = max(0.0, min(1.0, float(match.group(1))))
            else:
                logger.warning("Could not parse score from LLM response: %s", raw[:100])
                score = 0.5  # Default neutral score

            # Extract rationale
            rationale: str | None = None
            rationale_match = re.search(r'"rationale"\s*:\s*"([^"]*)"', raw)
            if rationale_match:
                rationale = rationale_match.group(1)

            return score, rationale

        except Exception as e:
            logger.warning("Scoring failed: %s", e)
            return 0.5, f"Scoring error: {e}"
