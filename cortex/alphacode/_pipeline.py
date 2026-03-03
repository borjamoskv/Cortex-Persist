# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""AlphaCode — Pipeline Orchestrator.

The complete 5-stage AlphaCode pipeline:

1. **Sample** — Generate N diverse solutions via LLM
2. **Filter** — Execute against example tests, discard failures
3. **Cluster** — Group by output signature on synthetic inputs
4. **Score** — LLM-judge each cluster representative
5. **Select** — Return top-K diverse submissions

Usage::

    from cortex.alphacode import AlphaCodePipeline, Problem, TestCase, AlphaCodeConfig
    from cortex.llm.provider import LLMProvider

    llm = LLMProvider(provider="gemini")
    pipeline = AlphaCodePipeline(llm=llm)

    problem = Problem(
        title="A+B",
        statement="Read two integers and print their sum.",
        example_tests=[TestCase(input="1 2", expected_output="3")],
    )

    result = await pipeline.solve(problem)
    print(result.best.solution.code)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from cortex.alphacode._clusterer import Clusterer
from cortex.alphacode._models import (
    AlphaCodeConfig,
    FilteredSolution,
    Problem,
    ScoredSolution,
    SubmissionSet,
)
from cortex.alphacode._runner import SandboxRunner
from cortex.alphacode._sampler import Sampler
from cortex.alphacode._scorer import Scorer

if TYPE_CHECKING:
    from cortex.llm.provider import LLMProvider

logger = logging.getLogger("cortex.alphacode.pipeline")


class AlphaCodePipeline:
    """Complete AlphaCode pipeline: Sample → Filter → Cluster → Score → Select.

    Integrates with CORTEX's LLM infrastructure for multi-provider support,
    and uses subprocess isolation for safe code execution.
    """

    def __init__(
        self,
        llm: LLMProvider,
        config: AlphaCodeConfig | None = None,
        *,
        scoring_llm: LLMProvider | None = None,
    ) -> None:
        """Initialize pipeline.

        Args:
            llm: Primary LLM provider for solution generation and clustering.
            config: Pipeline configuration. Uses defaults if None.
            scoring_llm: Optional separate LLM for scoring (can be cheaper/faster).
                        Falls back to primary llm if not provided.
        """
        self._config = config or AlphaCodeConfig()
        self._runner = SandboxRunner(
            timeout_seconds=self._config.execution_timeout_seconds,
        )
        self._sampler = Sampler(llm=llm, config=self._config)
        self._clusterer = Clusterer(llm=llm, runner=self._runner, config=self._config)
        self._scorer = Scorer(
            llm=scoring_llm or llm,
            temperature=self._config.scoring_temperature,
        )

    async def solve(self, problem: Problem) -> SubmissionSet:
        """Execute the full AlphaCode pipeline on a problem.

        Returns a SubmissionSet with the top-K diverse solutions,
        ranked by correctness score.
        """
        start = time.monotonic()

        # ── Stage 1: Sample ──────────────────────────────────────────
        logger.info("Stage 1/5: Sampling %d solutions...", self._config.num_samples)
        samples = await self._sampler.sample_all(problem)

        if not samples:
            logger.error("No samples generated — pipeline aborted")
            return self._empty_result(problem, start)

        # ── Stage 2: Filter ──────────────────────────────────────────
        logger.info("Stage 2/5: Filtering %d samples against example tests...", len(samples))
        filtered = await self._filter_solutions(samples, problem)

        if not filtered:
            logger.warning(
                "No solutions passed example tests — returning best-effort from %d samples",
                len(samples),
            )
            return self._empty_result(problem, start, total_sampled=len(samples))

        # ── Stage 3: Cluster ─────────────────────────────────────────
        logger.info("Stage 3/5: Clustering %d passed solutions...", len(filtered))
        clusters = await self._clusterer.cluster(filtered, problem)

        if not clusters:
            logger.warning("Clustering produced no clusters")
            return self._empty_result(
                problem, start,
                total_sampled=len(samples),
                total_filtered=len(filtered),
            )

        # ── Stage 4: Score ───────────────────────────────────────────
        if self._config.use_llm_scoring:
            logger.info("Stage 4/5: Scoring %d cluster representatives...", len(clusters))
            scored = await self._scorer.score_clusters(clusters, problem)
        else:
            # Skip scoring — use cardinality as proxy
            logger.info("Stage 4/5: Skipping LLM scoring, using cardinality ranking")
            scored = [
                ScoredSolution(
                    solution=c.representative,
                    cluster_id=c.cluster_id,
                    score=c.confidence,
                    scoring_model="cardinality",
                )
                for c in clusters
            ]

        # ── Stage 5: Select ──────────────────────────────────────────
        submissions = scored[: self._config.max_submissions]
        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "Stage 5/5: Selected %d submissions (%.1fs total)",
            len(submissions),
            elapsed_ms / 1000,
        )

        return SubmissionSet(
            problem_title=problem.title,
            solutions=tuple(submissions),
            total_sampled=len(samples),
            total_passed_filter=len(filtered),
            total_clusters=len(clusters),
            pipeline_duration_ms=elapsed_ms,
        )

    def _should_accept(self, solution: FilteredSolution) -> bool:
        """Check if a filtered solution meets the acceptance criteria."""
        if self._config.require_all_examples_pass:
            return solution.passed_all
        return solution.pass_rate > 0

    async def _filter_solutions(
        self,
        samples: list,
        problem: Problem,
    ) -> list[FilteredSolution]:
        """Filter solutions by executing against example test cases."""
        semaphore = asyncio.Semaphore(self._config.max_concurrent_executions)

        async def _run_one(sample) -> FilteredSolution:
            async with semaphore:
                return await self._runner.run_solution(
                    sample,
                    list(problem.example_tests),
                    problem.language,
                )

        tasks = [_run_one(s) for s in samples]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        filtered: list[FilteredSolution] = []
        for r in results:
            if isinstance(r, FilteredSolution) and self._should_accept(r):
                filtered.append(r)
            elif isinstance(r, Exception):
                logger.warning("Solution execution failed: %s", r)

        logger.info(
            "Filter: %d/%d solutions passed example tests (%.1f%% pass rate)",
            len(filtered),
            len(samples),
            (len(filtered) / len(samples) * 100) if samples else 0,
        )
        return filtered

    def _empty_result(
        self,
        problem: Problem,
        start: float,
        *,
        total_sampled: int = 0,
        total_filtered: int = 0,
    ) -> SubmissionSet:
        """Create an empty SubmissionSet for early-exit cases."""
        return SubmissionSet(
            problem_title=problem.title,
            solutions=(),
            total_sampled=total_sampled,
            total_passed_filter=total_filtered,
            total_clusters=0,
            pipeline_duration_ms=(time.monotonic() - start) * 1000,
        )
