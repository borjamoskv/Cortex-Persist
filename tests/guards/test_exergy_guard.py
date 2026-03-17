"""Tests for ExergyGuard."""

import pytest

from cortex.guards.exergy_guard import ExergyGuard, calculate_exergy


def test_calculate_exergy_empty() -> None:
    assert calculate_exergy("") == 0.0


def test_calculate_exergy_short_valid() -> None:
    # Extremely short phrases should pass (1.0) unless decorated
    assert calculate_exergy("deploy to production") == 1.0


def test_calculate_exergy_short_decorated() -> None:
    # Decorative in short text
    assert calculate_exergy("por supuesto aqui tienes") == 0.0


def test_calculate_exergy_high_density() -> None:
    text = "The migration requires dropping the users table and replacing it with accounts to ensure referential integrity."
    score = calculate_exergy(text)
    assert score > 0.6  # High density


def test_calculate_exergy_low_density() -> None:
    text = "Por supuesto, entendido. Como un modelo de lenguaje, espero que te sea útil resumir que la base de datos es SQL. Además, en conclusión, aquí tienes esto."
    score = calculate_exergy(text)
    assert score < 0.4  # Low density, a lot of decorative stuff


def test_exergy_guard_passes_valid_content() -> None:
    guard = ExergyGuard()
    text = "Implemented cryptographic signature verification for ledger entries."
    # Should not raise
    guard.check_thermodynamic_yield(text, "test-project", "decision")


def test_exergy_guard_raises_decorative() -> None:
    guard = ExergyGuard()
    text = "Por supuesto, entendido. Procedo a explicarte que el sistema funciona bien. Espero que te sea útil."
    with pytest.raises(ValueError) as exc:
        guard.check_thermodynamic_yield(text, "test-project", "thought")

    assert "Thermodynamic Violation" in str(exc.value)


def test_exergy_guard_ignores_non_text_fact_types() -> None:
    guard = ExergyGuard()
    text = "Por supuesto, entendido. Procedo a explicarte que el sistema funciona bien."
    # Even though text is low exergy, fact type 'code' bypasses check
    score = guard.check_thermodynamic_yield(text, "test-project", "code")
    assert score == 1.0
