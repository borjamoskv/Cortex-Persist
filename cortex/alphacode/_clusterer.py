# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""AlphaCode — Solution Clusterer.

Groups semantically equivalent solutions by their output signatures
on synthetically generated test inputs.

Architecture::

    Filtered Solutions → Generate Synthetic Inputs → Execute All → Signatures → Clusters
                              ↑ (LLM)                    ↑ (Sandbox)

Key insight from DeepMind: solutions that produce identical outputs
on diverse inputs are semantically equivalent, even if their code differs.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from cortex.alphacode._models import (
    AlphaCodeConfig,
    ClusterResult,
    FilteredSolution,
    Language,
    OutputSignature,
    Problem,
)
from cortex.alphacode._runner import SandboxRunner

if TYPE_CHECKING:
    from cortex.llm.provider import LLMProvider

logger = logging.getLogger("cortex.alphacode.clusterer")


_INPUT_GEN_SYSTEM = """\
You are a competitive programming test case generator.
Given a problem statement, generate a single valid test input.
- Follow the input format exactly as specified
- Generate edge cases and stress tests
- Output ONLY the raw test input, nothing else
- No explanations, no code fences"""


class Clusterer:
    """Group filtered solutions by output equivalence on synthetic inputs."""

    def __init__(
        self,
        llm: LLMProvider,
        runner: SandboxRunner,
        config: AlphaCodeConfig,
    ) -> None:
        self._llm = llm
        self._runner = runner
        self._config = config

    async def cluster(
        self,
        solutions: list[FilteredSolution],
        problem: Problem,
    ) -> list[ClusterResult]:
        """Cluster solutions by output signature.

        1. Generate synthetic test inputs via LLM
        2. Execute each solution on all synthetic inputs
        3. Group by output fingerprint
        4. Sort clusters by cardinality (largest = most confident)
        5. Return top-K clusters
        """
        if not solutions:
            return []

        # Step 1: Generate synthetic inputs
        synthetic_inputs = await self._generate_inputs(problem)
        if not synthetic_inputs:
            logger.warning("No synthetic inputs generated, each solution gets its own cluster")
            return self._trivial_clusters(solutions)

        # Step 2: Compute output signatures
        signatures = await self._compute_signatures(
            solutions, synthetic_inputs, problem.language
        )

        # Step 3: Group by signature
        groups: dict[str, list[FilteredSolution]] = defaultdict(list)
        sig_map: dict[str, OutputSignature] = {}
        for sol, sig in signatures:
            groups[sig.signature_hash].append(sol)
            sig_map[sig.signature_hash] = sig

        # Step 4: Build clusters, sorted by cardinality
        clusters: list[ClusterResult] = []
        for cluster_id, (sig_hash, members) in enumerate(
            sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)
        ):
            signature = sig_map[sig_hash]
            # Representative = first solution (could be enhanced with scoring)
            representative = members[0]
            clusters.append(
                ClusterResult(
                    cluster_id=cluster_id,
                    signature=signature,
                    solutions=tuple(members),
                    cardinality=len(members),
                    representative=representative,
                )
            )

        # Step 5: Truncate to max clusters
        result = clusters[: self._config.max_clusters]
        logger.info(
            "Clustered %d solutions into %d clusters (kept top %d)",
            len(solutions),
            len(clusters),
            len(result),
        )
        return result

    async def _generate_inputs(self, problem: Problem) -> list[str]:
        """Generate synthetic test inputs using LLM."""
        prompt_base = (
            f"Problem: {problem.title}\n\n"
            f"{problem.statement}\n\n"
            "Generate a single valid test input following the exact input format."
        )

        semaphore = asyncio.Semaphore(self._config.max_concurrent_samples)

        async def _gen_one(i: int) -> str | None:
            async with semaphore:
                try:
                    # Vary temperature to get diverse inputs
                    temp = 0.5 + (i / max(self._config.num_generated_inputs - 1, 1)) * 0.7
                    result = await self._llm.complete(
                        prompt=prompt_base,
                        system=_INPUT_GEN_SYSTEM,
                        temperature=temp,
                        max_tokens=512,
                    )
                    cleaned = result.strip()
                    if cleaned:
                        return cleaned
                except Exception as e:
                    logger.warning("Input generation %d failed: %s", i, e)
                return None

        tasks = [_gen_one(i) for i in range(self._config.num_generated_inputs)]
        results = await asyncio.gather(*tasks)

        inputs = [r for r in results if r is not None]
        logger.info("Generated %d synthetic test inputs", len(inputs))
        return inputs

    async def _compute_signatures(
        self,
        solutions: list[FilteredSolution],
        synthetic_inputs: list[str],
        language: Language,
    ) -> list[tuple[FilteredSolution, OutputSignature]]:
        """Execute all solutions on all synthetic inputs, compute signatures."""
        semaphore = asyncio.Semaphore(self._config.max_concurrent_executions)

        async def _compute_one(
            sol: FilteredSolution,
        ) -> tuple[FilteredSolution, OutputSignature]:
            outputs: list[str] = []
            for inp in synthetic_inputs:
                async with semaphore:
                    output = await self._runner.get_output_for_input(
                        sol.code, inp, language
                    )
                    outputs.append(output)
            return sol, OutputSignature.from_outputs(outputs)

        tasks = [_compute_one(sol) for sol in solutions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid: list[tuple[FilteredSolution, OutputSignature]] = []
        for r in results:
            if isinstance(r, tuple):
                valid.append(r)
            elif isinstance(r, Exception):
                logger.warning("Signature computation failed: %s", r)

        return valid

    @staticmethod
    def _trivial_clusters(solutions: list[FilteredSolution]) -> list[ClusterResult]:
        """Fallback: each solution in its own cluster."""
        return [
            ClusterResult(
                cluster_id=i,
                signature=OutputSignature.from_outputs([]),
                solutions=(sol,),
                cardinality=1,
                representative=sol,
            )
            for i, sol in enumerate(solutions)
        ]
