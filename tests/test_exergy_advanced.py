import pytest

from cortex.guards.exergy_guard import ExergyGuard, calculate_exergy


@pytest.mark.parametrize(
    "text, expected_min, description",
    [
        (
            "cortex-persist sovereign memory int8 quantization is-diamond=1",
            0.6,
            "Pure technical signal (High Exergy)"
        ),
        (
            "por supuesto aquí tienes el código espero que te sea muy útil en tu proyecto de software",
            0.0,
            "Pure decorative padding (Low Exergy)"
        ),
        (
            "the the the the the the the the the the the the the the the",
            0.0,
            "Repetitive loop (Low Exergy)"
        ),
        (
            "This implements a shannon-based entropy guard for the CORTEX-Persist engine.",
            0.45,
            "Concise technical note (Acceptable)"
        )
    ]
)
def test_aura_omega_metrics(text, expected_min, description):
    score = calculate_exergy(text)
    print(f"\n[TEST] {description}: '{text[:30]}...' -> Score: {score:.2f}")
    if expected_min > 0:
        assert score >= expected_min
    else:
        assert score < 0.45  # Default threshold in Aura-Omega

def test_exergy_guard_rejection():
    guard = ExergyGuard()
    # Should raise ValueError for padding
    with pytest.raises(ValueError, match="Thermodynamic Violation"):
        guard.check_thermodynamic_yield(
            "Hola! Por supuesto, te daré la información. Es muy importante notar que...",
            "test_proj",
            "decision"
        )

def test_technical_density_regex():
    # Supports underscores and dashes (Aura-Omega refinement)
    text = "vector_store_l2-alpha_variant_7"
    score = calculate_exergy(text)
    assert score > 0.8
