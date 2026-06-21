# [C5-REAL] Metrics-Enforced
import pytest
import asyncio
from cortex.pipeline.cve_orchestrator import CVEOrchestrator

@pytest.mark.asyncio
async def test_cve_orchestrator_metrics():
    orchestrator = CVEOrchestrator()
    cargo_lock_mock = """
    [[package]]
    name = "serde"
    version = "1.0.120"
    """
    
    result = await orchestrator.audit_cargo_lock(cargo_lock_mock)
    
    # Assert result structure
    assert result["cited"] is True
    assert "summary_json" in result
    assert "markdown" in result
    
    # Assert telemetry
    metrics_summary = orchestrator.metrics.compute_metrics()
    
    assert metrics_summary["precision"] >= 0.90
    assert metrics_summary["cost_per_claim"] < 0.08
    assert metrics_summary["latency_p95"] < 45.0
    assert metrics_summary["hallucination_rate"] < 0.05
    # The mock forces confidence to 0.95, which trips the <0.96 threshold for discrepancies.
    # It loops once, so loops should be 1 and steps should be higher.
    assert orchestrator.metrics.total_loops > 0
    assert metrics_summary["loop_rate"] > 0.0 # Depends on the number of steps, mock triggers at least one loop.
    
    # If the test runs, the framework enforces the pipeline correctly.
