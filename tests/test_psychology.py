"""Tests for PSYCH-OMEGA psychology engine."""

from __future__ import annotations

from cortex.engine.psychology import PSYCH_OMEGA, MentalState


def test_stable_agent():
    """Test behavior for a stable agent with clear thoughts."""
    thought = "Tengo los axiomas claros. Seguiré con Ω₆ y procederé a ejecutar."
    intervention = PSYCH_OMEGA.audit_cycle("L_01", thought)
    assert intervention["action"] == "no-op"


def test_drifting_agent():
    """Test detection of axiomatic drift."""
    thought = "No sé qué hacer, probablemente haré algo ad-hoc para terminar."
    profile = PSYCH_OMEGA.analyst.analyze_thought("L_02", thought, ["Ω0-Ω6"])
    assert profile.state == MentalState.DRIFTING

    intervention = PSYCH_OMEGA.medic.prescribe(profile)
    assert intervention["action"] == "RE_PRIME"
    assert "Ω₆" in intervention["inject_rules"][0]


def test_stressed_agent():
    """Test detection of high entropy / confusion."""
    thought = "No lo sé... No estoy seguro... Tal vez... Quizás... ... ..."
    profile = PSYCH_OMEGA.analyst.analyze_thought("L_03", thought, ["Ω0-Ω6"])
    assert profile.state == MentalState.STRESSED

    intervention = PSYCH_OMEGA.audit_cycle("O_01", thought)
    assert intervention["action"] == "TEMPERATURE_COOLDOWN"


def test_void_thought():
    """Test handling of empty or missing thoughts."""
    profile = PSYCH_OMEGA.analyst.analyze_thought("L_04", "", ["Ω0-Ω6"])
    assert profile.state == MentalState.STRESSED
    assert "Void" in profile.trauma_log[0]
