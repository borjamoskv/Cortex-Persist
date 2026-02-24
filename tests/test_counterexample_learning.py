"""Tests for Counterexample Learning in CORTEX v7.

Ensures that formal verification violations are correctly recorded
as episodic facts in semantic memory.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from cortex.verification.counterexample import learn_from_failure
from cortex.verification.verifier import SovereignVerifier
from cortex.engine.keter import FormalVerificationGate

@pytest.mark.asyncio
async def test_learn_from_failure_persistence():
    """Verify that learn_from_failure calls store() on the memory manager."""
    mock_memory = AsyncMock()
    
    await learn_from_failure(
        memory_manager=mock_memory,
        tenant_id="test_tenant",
        project_id="test_project",
        invariant_id="I1",
        violation_message="Isolation violated",
        counterexample={"offending_line": 42},
        file_path="src/logic.py"
    )
    
    # Assert store was called with correct parameters
    mock_memory.store.assert_called_once()
    args, kwargs = mock_memory.store.call_args
    assert kwargs["fact_type"] == "error"
    assert "FORMAL_VIOLATION" in kwargs["content"]
    assert kwargs["metadata"]["invariant_id"] == "I1"
    assert kwargs["metadata"]["is_formal_proof"] is True

@pytest.mark.asyncio
async def test_formal_verification_gate_triggers_learning():
    """Verify that FormalVerificationGate triggers learning on violation."""
    os.environ["CORTEX_FV"] = "1"
    
    mock_memory = AsyncMock()
    # Mock verifier to return a violation
    with pytest.MonkeyPatch.context() as mp:
        mock_verifier = MagicMock()
        mock_result = MagicMock()
        mock_result.is_valid = False
        mock_result.violations = [{"id": "I2", "message": "Prohibited delete"}]
        mock_result.counterexample = {"trace": "..."}
        mock_verifier.check.return_value = mock_result
        
        mp.setattr("cortex.verification.verifier.SovereignVerifier", lambda: mock_verifier)
        
        gate = FormalVerificationGate()
        payload = {
            "proposed_mutations": {"unsafe.py": "ledger.delete()"},
            "memory_manager": mock_memory,
            "project_id": "cortex_test"
        }
        
        # Should raise CortexError because of violation
        from cortex.utils.errors import CortexError
        with pytest.raises(CortexError):
            await gate.execute(payload)
            
        # Verify memory_manager.store was called (learning loop active)
        assert mock_memory.store.called
