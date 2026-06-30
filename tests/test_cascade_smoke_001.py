# [C5-REAL] Exergy-Maximized
"""CORTEX Smoke Test 001 - Cascade & SICA Feedback.

Verifies:
1. AsyncCascadeRouter routing correctly using 'implement' keyword.
2. MetaLevel intercepting a 'cascade_failure' and mutating the genome.
3. Smoke integration for the PR body.
"""

import asyncio
import pytest
from babylon60.router.router import AgentRouter, AgentCapability
from babylon60.router.cascade import AsyncCascadeRouter
from babylon60.sica.object_level import ExecutionTrace, StepOutcome
from babylon60.sica.meta_level import MetaLevel, FailureClass
from babylon60.sica.strategy import SearchStrategy, StrategyGenome


@pytest.mark.asyncio
async def test_cascade_smoke_001():
    # 1. Test Router Mapping (Keyword 'implement' -> code-engineer)
    base_router = AgentRouter()
    cascade_router = AsyncCascadeRouter(base_router, max_retries=1, base_delay=0.1)

    decision = await cascade_router.route_with_retry(
        intent="implement authentication module", budget_remaining=0.5
    )

    assert "code-engineer" in decision["agents"]
    assert decision["strategy"] in ["sequential", "cascade"]
    print(f"\n[ROUTER OK] Decision: {decision}")

    # 2. Test SICA MetaLevel Cascade Blindness interception
    strategy = SearchStrategy(StrategyGenome())
    meta = MetaLevel(strategy=strategy)

    # Simulate a trace that failed continuously (cascade_failure)
    trace = ExecutionTrace(
        task_id="smoke-test-task",
        objective="implement feature",
        strategy_genome_hash=strategy.genome.genome_hash,
    )
    trace.error_pattern = "cascade_failure"
    trace.final_outcome = StepOutcome.FAILURE

    # Monitor should detect CASCADE_BLINDNESS
    judgment = meta.monitor(trace)
    assert judgment.failure_class == FailureClass.CASCADE_BLINDNESS
    assert judgment.is_meta_failure is True
    print(f"[META-LEVEL OK] Judgment Diagnosed: {judgment.diagnosis}")

    # Control should mutate the strategy based on the judgment
    mutations = meta.control(judgment)
    assert len(mutations) > 0
    print(f"[MUTATION OK] Strategy Mutated: {mutations}")
