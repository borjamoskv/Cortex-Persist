import pytest
from cortex.guards.thermodynamic import ThermodynamicCounters, should_enter_decorative_mode


def test_should_enter_decorative_mode_happy():
    """Happy path: System is healthy, returns False."""
    c = ThermodynamicCounters(
        consecutive_tool_fails_without_new_hypothesis=0,
        file_reads_without_ast_delta=0,
        context_expansion_rate=1.0,
        uncertainty_reduction_rate=1.5,
        causal_taint_count=0,
    )
    result, reasons = should_enter_decorative_mode(c)
    assert result is False
    assert len(reasons) == 0


def test_should_enter_decorative_mode_rejection():
    """Rejection path: Multiple triggers matched."""
    c = ThermodynamicCounters(
        consecutive_tool_fails_without_new_hypothesis=4,
        file_reads_without_ast_delta=6,
        context_expansion_rate=2.0,
        uncertainty_reduction_rate=0.5,  # Metastability 0.25 (still >0.2), context_expansion > reduction
        causal_taint_count=12,
    )
    result, reasons = should_enter_decorative_mode(c)
    assert result is True
    assert len(reasons) == 4  # >3 fails, >5 reads, context>reduction, >10 taint


def test_should_enter_decorative_mode_boundary():
    """Boundary condition: Testing the exact limits of the triggers."""
    # Fails exactly at threshold
    c1 = ThermodynamicCounters(consecutive_tool_fails_without_new_hypothesis=3)
    result1, reasons1 = should_enter_decorative_mode(c1)
    assert result1 is True
    assert "tool_fails_without_new_hypothesis>=3" in reasons1

    # Just below threshold
    c2 = ThermodynamicCounters(consecutive_tool_fails_without_new_hypothesis=2)
    # Note: metastability will trigger if context=0 and reduction=0? No, if context=0, probe returns 1.0
    result2, reasons2 = should_enter_decorative_mode(c2)
    assert result2 is False

    # Testing metastability < 0.2
    c3 = ThermodynamicCounters(context_expansion_rate=1.0, uncertainty_reduction_rate=0.1)
    result3, reasons3 = should_enter_decorative_mode(c3)
    assert result3 is True
    assert any("metastability_index<0.2" in r for r in reasons3)
    assert any("context_expansion_rate>uncertainty_reduction_rate" in r for r in reasons3)

    # Context expansion == uncertainty reduction
    c4 = ThermodynamicCounters(context_expansion_rate=1.0, uncertainty_reduction_rate=1.0)
    result4, reasons4 = should_enter_decorative_mode(c4)
    assert result4 is False
