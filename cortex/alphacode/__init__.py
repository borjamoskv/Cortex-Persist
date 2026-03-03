# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX AlphaCode — Competitive Programming Solver.

DeepMind AlphaCode-inspired pipeline for autonomous code generation:

1. **Massive Sampling** — Generate N candidate solutions via LLM at high temperature
2. **Filtering** — Execute against example test cases, discard failures
3. **Clustering** — Group survivors by output signature on generated inputs
4. **Scoring** — Rank clusters by cardinality, select best per cluster
5. **Submission** — Return top-K diverse solutions

Architecture::

    Problem → Sampler → Filter → Clusterer → Scorer → Solutions
                ↓           ↓          ↓           ↓
           LLMProvider   Sandbox   Signature    LLM Judge
"""

from cortex.alphacode._models import (
    AlphaCodeConfig,
    ClusterResult,
    FilteredSolution,
    Problem,
    SampledSolution,
    ScoredSolution,
    SubmissionSet,
    TestCase,
)
from cortex.alphacode._pipeline import AlphaCodePipeline

__all__ = [
    "AlphaCodeConfig",
    "AlphaCodePipeline",
    "ClusterResult",
    "FilteredSolution",
    "Problem",
    "SampledSolution",
    "ScoredSolution",
    "SubmissionSet",
    "TestCase",
]
