# [C5-REAL] Exergy-Maximized
"""
Tests for CORTEX v1.0 Entropy Core
"""

import pytest
from pathlib import Path
from babylon60.engine.entropy_core import EntropyCore, EntropyState, SystemRegime
from babylon60.guards.entropy_guard import EntropyGuardEngine, GuardAction
from babylon60.engine.decision_engine import DecisionEngine

@pytest.fixture
def mock_workspace(tmp_path):
    # Create a dummy python file to be scanned by EntropyAnnihilator
    dummy_file = tmp_path / "dummy.py"
    dummy_file.write_text("class A:\n  def f(self):\n    pass\n")
    return tmp_path

def test_entropy_core_evaluation(mock_workspace):
    core = EntropyCore(str(mock_workspace))
    
    # We pretend the dummy file was modified
    state = core.evaluate_entropy(
        diff_content="+class A:\n+  def f(self):\n+    pass\n",
        intent_prompt="Add class A with method f",
        modified_files=["dummy.py"]
    )
    
    assert isinstance(state, EntropyState)
    assert state.structural >= 0.0
    assert state.semantic >= 0.0
    assert state.operational >= 0.0
    assert isinstance(state.regime, SystemRegime)

def test_entropy_guard_decision():
    guard = EntropyGuardEngine()
    
    # Simulate a critical state
    critical_state = EntropyState(
        structural=0.9, # Exceeds threshold 0.8
        semantic=0.1,
        operational=0.1,
        total=0.9,
        regime=SystemRegime.CRITICAL
    )
    
    decision = guard.evaluate(critical_state)
    assert decision.status == GuardAction.BLOCK
    assert len(decision.reasons) > 0

def test_decision_engine_resolution():
    guard = EntropyGuardEngine()
    decision_engine = DecisionEngine()
    
    collapse_state = EntropyState(
        structural=0.9,
        semantic=0.9,
        operational=0.9,
        total=0.9,
        regime=SystemRegime.COLLAPSE
    )
    
    guard_decision = guard.evaluate(collapse_state)
    resolution = decision_engine.resolve(collapse_state, guard_decision)
    
    assert resolution.action == GuardAction.BLOCK
    assert "SYSTEM COLLAPSE" in resolution.feedback
