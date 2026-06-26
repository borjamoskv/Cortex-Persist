import pytest
from scripts.bounty_guard import BountyGuard

def test_production_bounty_guard_firedancer():
    # Setup
    guard = BountyGuard()
    
    # In-scope
    u1 = "https://github.com/firedancer-io/firedancer/src/core.c"
    allowed, reason, pid = guard.validate_target(u1)
    assert allowed is True
    assert pid == "firedancer-v1"
    
    # Out-of-scope (API meta)
    u2 = "https://api.firedancer.io/v1/meta"
    allowed2, reason2, pid2 = guard.validate_target(u2)
    assert allowed2 is False
    assert "out-of-scope" in reason2

def test_production_bounty_guard_unmatched():
    guard = BountyGuard()
    u3 = "https://google.com"
    allowed, reason, pid = guard.validate_target(u3)
    assert allowed is False
    assert "No matching policy" in reason

if __name__ == "__main__":
    pytest.main([__file__])
