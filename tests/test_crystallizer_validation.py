# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon60.engine.crystallizer import AutoCrystallizer, SovereignFactSchema


def test_validation_success():
    crystallizer = AutoCrystallizer()
    valid_data = [
        {
            "project": "alpha",
            "content": "Axiom 1: Clean code is clean.",
            "provenance": "agent-1",
            "confidence_score": 0.95,
            "fact_type": "knowledge",
            "tags": ["axiom", "c5-real"],
            "metadata": {"source_session": "session-1"},
        },
        {
            "project": "beta",
            "content": "Axiom 2: Anergy is the death.",
            "provenance": "agent-2",
            "confidence_score": 1.0,
        },
    ]
    results = crystallizer.validate_facts_json(valid_data)
    assert len(results) == 2
    assert results[0]["project"] == "alpha"
    assert results[0]["provenance"] == "agent-1"
    assert results[0]["confidence_score"] == 0.95
    assert results[1]["confidence_score"] == 1.0


def test_validation_missing_provenance():
    crystallizer = AutoCrystallizer()
    invalid_data = [
        {
            "project": "alpha",
            "content": "Some content",
            # missing provenance
            "confidence_score": 0.8,
        }
    ]
    with pytest.raises(ValidationError) as excinfo:
        crystallizer.validate_facts_json(invalid_data)
    assert "provenance" in str(excinfo.value)


def test_validation_missing_confidence_score():
    crystallizer = AutoCrystallizer()
    invalid_data = [
        {
            "project": "alpha",
            "content": "Some content",
            "provenance": "agent-1",
            # missing confidence_score
        }
    ]
    with pytest.raises(ValidationError) as excinfo:
        crystallizer.validate_facts_json(invalid_data)
    assert "confidence_score" in str(excinfo.value)


def test_validation_invalid_confidence_score_range():
    crystallizer = AutoCrystallizer()
    # Score > 1.0
    invalid_data_high = [
        {
            "project": "alpha",
            "content": "Some content",
            "provenance": "agent-1",
            "confidence_score": 1.1,
        }
    ]
    with pytest.raises(ValidationError) as excinfo:
        crystallizer.validate_facts_json(invalid_data_high)
    assert "confidence_score" in str(excinfo.value)

    # Score < 0.0
    invalid_data_low = [
        {
            "project": "alpha",
            "content": "Some content",
            "provenance": "agent-1",
            "confidence_score": -0.1,
        }
    ]
    with pytest.raises(ValidationError) as excinfo:
        crystallizer.validate_facts_json(invalid_data_low)
    assert "confidence_score" in str(excinfo.value)


def test_validation_invalid_json_format():
    crystallizer = AutoCrystallizer()
    invalid_json_str = "{invalid json"
    with pytest.raises(ValueError, match="Invalid JSON format"):
        crystallizer.validate_facts_json(invalid_json_str)


def test_validation_non_list_input():
    crystallizer = AutoCrystallizer()
    invalid_input = {"project": "alpha"}
    with pytest.raises(ValueError, match="Input data must be a list of facts"):
        crystallizer.validate_facts_json(invalid_input)
