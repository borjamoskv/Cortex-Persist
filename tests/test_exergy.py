import pytest

from cortex.shannon.exergy import (
    ActionRisk,
    ExergyInput,
    ThermodynamicWasteError,
    calculate_exergy,
    enforce_exergy,
)


def test_exergy_reduces_uncertainty_low_cost():
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=0.1,
        tokens_consumed=100,
        action_risk=ActionRisk.READ_ONLY,
        had_backup=True,
        touched_persistent_state=False,
    )
    result = calculate_exergy(inp, threshold_min_work=0.001)
    assert not result.below_threshold
    assert result.score > 0
    enforce_exergy(result)  # Should not raise


def test_exergy_waste_tokens():
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=1.0,  # no reduction
        tokens_consumed=5000,
        action_risk=ActionRisk.READ_ONLY,
        had_backup=True,
        touched_persistent_state=False,
    )
    result = calculate_exergy(inp, threshold_min_work=0.001)
    assert result.below_threshold
    with pytest.raises(ThermodynamicWasteError):
        enforce_exergy(result)


def test_destructive_without_backup_negative_score():
    inp = ExergyInput(
        prior_uncertainty=1.0,
        posterior_uncertainty=0.5,
        tokens_consumed=10,
        action_risk=ActionRisk.DESTRUCTIVE,
        had_backup=False,
        touched_persistent_state=True,
    )
    result = calculate_exergy(inp, threshold_min_work=0.0)
    assert result.score < 0
    assert result.below_threshold
