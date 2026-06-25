import pytest
from legacy_research.engine.causal.decision_parser import DecisionParser, CausalInvariant
from legacy_research.engine.causality_models import ValidationStatus, KRGSE_DERIVED_FROM

def test_parse_decision_valid():
    parser = DecisionParser()
    payload = "def new_func():\n    return 42\n"
    context = {"agent_id": "test_agent", "session_id": "session_123"}
    
    invariant = parser.parse_decision(payload, context)
    
    assert isinstance(invariant, CausalInvariant)
    assert invariant.edge_type == KRGSE_DERIVED_FROM
    assert invariant.validation_status == ValidationStatus.TEST_PASSED
    assert invariant.confidence_b60 == 60
    assert invariant.metadata["agent_id"] == "test_agent"
    assert "taint:test_agent:session_123:" in invariant.metadata["cortex_taint"]

def test_parse_decision_tentative():
    parser = DecisionParser()
    payload = "def new_func():\n    # TODO: implement this\n    pass\n"
    context = {"agent_id": "test_agent"}
    
    invariant = parser.parse_decision(payload, context)
    
    assert invariant.validation_status == ValidationStatus.CONJECTURE
    assert invariant.confidence_b60 == 30

def test_parse_decision_empty_payload():
    parser = DecisionParser()
    with pytest.raises(ValueError):
        parser.parse_decision("", {})
