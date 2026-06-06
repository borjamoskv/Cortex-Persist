# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import AsyncMock
from cortex.verification.counterexample import learn_from_failure


@pytest.mark.asyncio
async def test_learn_from_failure():
    memory_manager = AsyncMock()
    await learn_from_failure(
        memory_manager=memory_manager,
        tenant_id="tenant-123",
        project_id="project-456",
        invariant_id="I1",
        violation_message="Test violation",
        counterexample={"key": "value"},
        file_path="test_file.py",
    )

    memory_manager.store.assert_called_once()
    kwargs = memory_manager.store.call_args.kwargs
    assert kwargs["tenant_id"] == "tenant-123"
    assert kwargs["project_id"] == "project-456"
    assert kwargs["fact_type"] == "error"
    assert "FORMAL_VIOLATION: Invariant I1 violated in test_file.py" in kwargs["content"]
    assert kwargs["metadata"]["source"] == "z3_verifier"
    assert kwargs["metadata"]["invariant_id"] == "I1"
    assert kwargs["metadata"]["file_path"] == "test_file.py"
    assert kwargs["metadata"]["is_formal_proof"] is True
    assert kwargs["metadata"]["confidence"] == "C5"
    assert kwargs["metadata"]["is_toxic"] is True
