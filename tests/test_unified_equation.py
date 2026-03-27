import pytest
from cortex.engine.mixins.exergy_mixin import ExergyMixin

class EngineWithExergy(ExergyMixin):
    pass

@pytest.fixture
def engine():
    return EngineWithExergy()

def test_compute_exergy_v3_positive_yield(engine):
    # High causal reduction, low entropy injection => Solid State convergence viable
    exergy = engine.compute_exergy_v3(
        causal_gap_reduction=0.9,
        weight=5.0,
        entropy_injected=0.1,
        cost_lambda=2.0
    )
    # (0.9 * 5.0) - (0.1 * 2.0) = 4.5 - 0.2 = 4.3
    assert exergy > 0.0
    assert exergy == 4.3

def test_compute_exergy_v3_negative_yield(engine):
    # Low causal reduction, high thermal noise (hallucination/drift)
    exergy = engine.compute_exergy_v3(
        causal_gap_reduction=0.1,
        weight=2.0,
        entropy_injected=0.8,
        cost_lambda=5.0
    )
    # (0.1 * 2.0) - (0.8 * 5.0) = 0.2 - 4.0 = -3.8
    assert exergy < 0.0
    assert exergy == -3.8

def test_check_solid_state_valid(engine):
    metrics = {
        "entropy_injection": 0.5,
        "dissipation_capacity": 1.0,
        "exergy_gradient": 0.1,
        "causal_integrity": True
    }
    assert engine.check_solid_state(metrics) is True

def test_check_solid_state_invalid_causality(engine):
    metrics = {
        "entropy_injection": 0.5,
        "dissipation_capacity": 1.0,
        "exergy_gradient": 0.1,
        "causal_integrity": False  # Fails here
    }
    assert engine.check_solid_state(metrics) is False

def test_check_solid_state_high_entropy(engine):
    metrics = {
        "entropy_injection": 1.5,
        "dissipation_capacity": 1.0,  # Fails here
        "exergy_gradient": 0.1,
        "causal_integrity": True
    }
    assert engine.check_solid_state(metrics) is False

def test_thermodynamic_contract_validation(engine):
    contract = {
        "exergy_min": 0.82
    }
    assert engine.validate_thermodynamic_contract(1.0, contract) is True
    assert engine.validate_thermodynamic_contract(0.5, contract) is False

def test_silent_collapse_prevention(engine):
    # Emulates a state where exergy is somehow high but causal integrity is compromised
    # The promotion gate / solid state trigger MUST block this.
    metrics = {
        "entropy_injection": 0.2,
        "dissipation_capacity": 1.0,
        "exergy_gradient": 5.0, # High exergy
        "causal_integrity": False # But invalid ledger causal chain
    }
    assert engine.check_solid_state(metrics) is False
