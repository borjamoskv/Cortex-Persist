# [C5-REAL] Exergy-Maximized
"""Tests for the B2B Context Compressor."""

import pytest

from cortex.extensions.sales_b2b.context_compressor import ContextCompressor


def test_compressor_degradation_threshold():
    """Verify context is flagged as degraded only when it exceeds entropy limits."""
    compressor = ContextCompressor(entropy_threshold=50)
    
    assert not compressor.is_degraded("Short text")
    assert compressor.is_degraded("This is a very long text that clearly exceeds the 50 characters threshold set above.")


def test_compressor_extracts_invariants():
    """Verify that the compressor extracts structural invariants and CORTEX-TAINT."""
    compressor = ContextCompressor()
    
    history = [
        {"timestamp": "2026-06-21T10:00:00Z", "content": "Hi, we are interested but it seems too expensive right now."},
        {"timestamp": "2026-06-22T10:00:00Z", "content": "Also, does it have an API integration?"}
    ]
    
    invariants = compressor.compress_history(history, agent_id="test_agent")
    
    assert invariants["total_interactions"] == 2
    assert invariants["last_contact_date"] == "2026-06-22T10:00:00Z"
    assert "BUDGET_OBJECTION" in invariants["extracted_topics"]
    assert "API_INTEGRATION" in invariants["extracted_topics"]
    assert len(invariants["compression_hash"]) == 16
    assert "[CORTEX-TAINT: test_agent]" in invariants["taint_signature"]
