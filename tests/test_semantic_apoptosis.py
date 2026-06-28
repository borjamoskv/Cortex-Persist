# [C5-REAL] Exergy-Maximized
"""
Unit tests for the SemanticApoptosisGuard (Information Bottleneck).
"""

import pytest
from cortex.guards.semantic_apoptosis_guard import SemanticApoptosisGuard, SemanticApoptosisError


def test_semantic_apoptosis_pure_code_or_data():
    guard = SemanticApoptosisGuard()

    # Pure JSON or structural dictionary should pass
    assert guard.assess_payload({"key": "value"}) is True

    # Pure code blocks with zero noise
    pure_code = "```python\ndef run_loop():\n    pass\n```"
    assert guard.assess_payload(pure_code) is True


def test_semantic_apoptosis_conversational_slop():
    guard = SemanticApoptosisGuard(max_noise_ratio=0.15)

    # Conversational slop with no code must immediately raise exception
    slop_only = (
        "Of course, here is the detailed explanation of how to optimize the causal engine."
    )
    with pytest.raises(SemanticApoptosisError, match="consists entirely of conversational slop"):
        guard.assess_payload(slop_only)


def test_semantic_apoptosis_mixed_payload():
    guard = SemanticApoptosisGuard(max_noise_ratio=0.10)

    # Mixed content with high prose ratio and slop markers must be rejected
    mixed_bad = (
        "Here is the code you requested for SQLite.\n"
        "```python\n"
        "import sqlite3\n"
        "```\n"
        "I hope this helps you mitigate chaos."
    )
    with pytest.raises(SemanticApoptosisError, match="exceeds strict boundary"):
        guard.assess_payload(mixed_bad)


def test_semantic_apoptosis_fast_path_eligibility():
    guard = SemanticApoptosisGuard(max_noise_ratio=0.15)

    # Structural code with negligible explanation/noise (no slop keywords)
    structural_good = "# [C5-REAL]\n```python\nclass MockEngine:\n    pass\n```"
    # Under 5% noise and 0 slop markers should trigger fast-path
    is_fast_path = guard.assess_payload(structural_good)
    assert is_fast_path is True
