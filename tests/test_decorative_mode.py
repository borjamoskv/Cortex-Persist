from cortex.guards.thermodynamic import ThermodynamicCounters, should_enter_decorative_mode


def test_decorative_mode_triggers():
    # 3 failures without new hypothesis -> triggering
    c1 = ThermodynamicCounters(consecutive_tool_fails_without_new_hypothesis=3)
    triggered, reasons = should_enter_decorative_mode(c1)
    assert triggered
    assert "tool_fails_without_new_hypothesis>=3" in reasons

    # 5 reads without AST delta -> triggering
    c2 = ThermodynamicCounters(file_reads_without_ast_delta=5)
    triggered, reasons = should_enter_decorative_mode(c2)
    assert triggered
    assert "file_reads_without_ast_delta>=5" in reasons

    # context expansion > reduction -> triggering
    c3 = ThermodynamicCounters(context_expansion_rate=0.5, uncertainty_reduction_rate=0.1)
    triggered, reasons = should_enter_decorative_mode(c3)
    assert triggered
    assert "context_expansion_rate>uncertainty_reduction_rate" in reasons


def test_not_decorative():
    c = ThermodynamicCounters(
        consecutive_tool_fails_without_new_hypothesis=1,
        file_reads_without_ast_delta=2,
        context_expansion_rate=0.1,
        uncertainty_reduction_rate=0.5,
    )
    triggered, reasons = should_enter_decorative_mode(c)
    assert not triggered
    assert len(reasons) == 0
