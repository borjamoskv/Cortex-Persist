# [C5-REAL] Tests for DAME engine module
# Anchored: tests/engine/test_dame.py
# Creator: Borja Moskv (borjamoskv)

import os
import asyncio
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from babylon60.engine.dame import DAMEState, DAMEExecutor, DAMEAsyncDelegator, DAMEApoptosisError

@pytest.mark.asyncio
async def test_dame_state_persistence():
    with TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "dame_state.json"
        state = DAMEState(state_path)
        
        # Test initial state is empty
        assert state.get("key1") is None
        
        # Test update and save
        state.update("key1", "value1")
        assert state.get("key1") == "value1"
        
        # Test loading from file
        new_state = DAMEState(state_path)
        assert new_state.get("key1") == "value1"

@pytest.mark.asyncio
async def test_dame_executor_exit_conditions():
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        state_path = tmp_path / "dame_state.json"
        state = DAMEState(state_path)
        executor = DAMEExecutor(state, max_retries=3)

        # Create validation script returning 0 (success)
        success_script = tmp_path / "success.sh"
        with open(success_script, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(success_script, 0o755)

        # Create validation script returning 1 (failure)
        fail_script = tmp_path / "fail.sh"
        with open(fail_script, "w") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(fail_script, 0o755)

        executed_count = 0
        def mock_payload():
            nonlocal executed_count
            executed_count += 1

        # Test success case
        res = await executor.execute_with_assertion(
            task_id="task_success",
            execution_coro=mock_payload,
            validation_script_path=success_script
        )
        assert res is True
        assert executed_count == 1
        assert state.get("retry_count_task_success") == 0
        assert state.get("status_task_success") == "COMPLETED"

        # Test failure case
        res_fail = await executor.execute_with_assertion(
            task_id="task_fail",
            execution_coro=mock_payload,
            validation_script_path=fail_script
        )
        assert res_fail is False
        assert executed_count == 2
        assert state.get("retry_count_task_fail") == 1

        # Test apoptosis trigger
        state.update("retry_count_task_fail", 3)
        with pytest.raises(DAMEApoptosisError):
            await executor.execute_with_assertion(
                task_id="task_fail",
                execution_coro=mock_payload,
                validation_script_path=fail_script
            )

@pytest.mark.asyncio
async def test_dame_async_delegator():
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        task = await DAMEAsyncDelegator.delegate_task(
            task_id="async_test",
            cmd=["echo", "decoupled_exergy"],
            log_dir=tmp_path
        )
        await task
        
        log_file = tmp_path / "async_test.log"
        assert log_file.exists()
        with open(log_file, "r") as f:
            content = f.read().strip()
        assert "decoupled_exergy" in content
