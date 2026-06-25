# [C5-REAL] Exergy-Maximized
"""
Unit tests for the Sanhedrin Monte Carlo Downsampling engine.
"""

import pytest
from cortex.engine.mcts_sanhedrin import (
    VectorialDownsampling,
    ContextFusionEngine,
    ConstraintFirewall,
)

@pytest.mark.asyncio
async def test_vectorial_downsampling():
    """Verify that VectorialDownsampling executes successfully and returns the expected consensus vector."""
    downsampling = VectorialDownsampling(tenant_id="test-tenant")
    intent = {"token_a": 0.8, "token_b": 0.2}
    res = await downsampling.execute_monte_carlo_nodes(intent)
    assert len(res["node_hash"]) == 16
    assert isinstance(res["node_hash"], str)
    assert res["entropy_variance"] == 0.12
    assert res["selected_path"] == "exploitation_dominant"

def test_context_fusion_engine_low_entropy():
    """Verify that ContextFusionEngine selects higher temperature for low entropy context."""
    engine = ContextFusionEngine()
    # length = 100 -> base_entropy = 100 * 60 // 1000 = 6 <= 500 -> temperature = 0.7
    res = engine.normalize_distribution("a" * 50, "b" * 50, "intent")
    assert res["normalized_entropy"] == 6
    assert res["dynamic_temperature"] == 0.7
    assert len(res["fused_vector_hash"]) == 16

def test_context_fusion_engine_high_entropy():
    """Verify that ContextFusionEngine drops the temperature to enforce coherence when entropy is high."""
    engine = ContextFusionEngine()
    # length = 9000 -> base_entropy = 9000 * 60 // 1000 = 540 > 500 -> temperature = 0.2
    res = engine.normalize_distribution("a" * 4500, "b" * 4500, "intent")
    assert res["normalized_entropy"] == 540
    assert res["dynamic_temperature"] == 0.2
    assert len(res["fused_vector_hash"]) == 16

def test_constraint_firewall_allowed():
    """Verify that ConstraintFirewall allows nodes with low entropy variance."""
    firewall = ConstraintFirewall()
    assert firewall.enforce_clipping({"entropy_variance": 0.12}) is True
    assert firewall.enforce_clipping({"entropy_variance": 0.50}) is True

def test_constraint_firewall_clipped():
    """Verify that ConstraintFirewall annihilates nodes exceeding entropy threshold."""
    firewall = ConstraintFirewall()
    assert firewall.enforce_clipping({"entropy_variance": 0.51}) is False
    assert firewall.enforce_clipping({}) is False  # Defaults to 1.0 > 0.5 -> False
