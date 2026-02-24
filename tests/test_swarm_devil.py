import pytest
from cortex.mejoralo.swarm import MejoraloSwarm

def test_devils_advocate_injection():
    swarm = MejoraloSwarm(level=2)
    # Simulate a complex finding string (more than 3 findings)
    findings = "- Issue 1\n- Issue 2\n- Issue 3\n- Issue 4"
    specialists = swarm._select_specialists(findings)
    assert "DevilsAdvocate" in specialists, "Devil's Advocate should be injected for complex tasks"
    
def test_devils_advocate_not_injected():
    swarm = MejoraloSwarm(level=1)
    # Simulate a simple finding string
    findings = "- Issue 1"
    specialists = swarm._select_specialists(findings)
    assert "DevilsAdvocate" not in specialists, "Devil's Advocate should NOT be injected for simple tasks"

