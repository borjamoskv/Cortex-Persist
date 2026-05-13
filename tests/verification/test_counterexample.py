import pytest
from unittest.mock import AsyncMock

from cortex.verification.counterexample import learn_from_failure


@pytest.mark.asyncio
async def test_learn_from_failure():
    memory_manager = AsyncMock()

    await learn_from_failure(
        memory_manager=memory_manager,
        tenant_id="tenant-123",
        project_id="proj-456",
        invariant_id="I2",
        violation_message="Prohibited delete",
        counterexample={"line": 42},
        file_path="src/main.py",
    )

    memory_manager.store.assert_called_once()
    kwargs = memory_manager.store.call_args.kwargs

    assert kwargs["tenant_id"] == "tenant-123"
    assert kwargs["project_id"] == "proj-456"
    assert "FORMAL_VIOLATION: Invariant I2 violated in src/main.py" in kwargs["content"]
    assert "Message: Prohibited delete" in kwargs["content"]
    assert "Counterexample detected: {'line': 42}" in kwargs["content"]
    assert kwargs["fact_type"] == "error"
    assert kwargs["metadata"]["source"] == "z3_verifier"
    assert kwargs["metadata"]["invariant_id"] == "I2"
    assert kwargs["metadata"]["file_path"] == "src/main.py"
    assert kwargs["metadata"]["is_formal_proof"] is True
    assert kwargs["metadata"]["confidence"] == "C5"
    assert kwargs["metadata"]["is_toxic"] is True
