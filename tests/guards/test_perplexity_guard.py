import pytest
from legacy_research.guards.perplexity_guard import PerplexityGuard

def test_perplexity_guard_passes_valid_text():
    guard = PerplexityGuard(threshold=8.5)
    valid_text = "This is a normal sentence with standard vocabulary and structure."
    result = guard.evaluate(valid_text)
    
    assert result["passed"] is True
    assert result["score"] <= 8.5

def test_perplexity_guard_rejects_high_entropy():
    guard = PerplexityGuard(threshold=8.5)
    # Simulate high-entropy random characters/base64 noise
    noise_text = "a x Z d E R T y Q P l M N b V c X Z a q w e r t y u i o p"
    result = guard.evaluate(noise_text)
    
    assert result["passed"] is False
    assert result["score"] > 8.5

def test_perplexity_guard_handles_empty_input():
    guard = PerplexityGuard(threshold=8.5)
    result = guard.evaluate("")
    
    assert result["passed"] is False
    assert result["score"] == float('inf')
