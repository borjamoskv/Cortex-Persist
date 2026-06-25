import pytest

from legacy_research.shannon.exergy import calculate_informational_exergy


def test_calculate_informational_exergy():
    # C_v = 5 verifiable transformations, T_u = 1000 tokens
    result = calculate_informational_exergy(5, 1000)
    assert result.info_exergy == 0.005
    assert result.verifiable_transformations == 5
    assert result.context_useful_tokens == 1000

def test_calculate_informational_exergy_zero_tokens():
    with pytest.raises(ValueError):
        calculate_informational_exergy(5, 0)
