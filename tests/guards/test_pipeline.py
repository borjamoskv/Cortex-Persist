# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
from unittest.mock import AsyncMock, patch
from legacy_research.guards.seals import _execute_gates_loop


@pytest.mark.asyncio
async def test_pipeline_execution_order():
    # Track execution order
    execution_order = []

    async def mock_gate_1():
        execution_order.append(1)
        return True, "verified"

    async def mock_gate_2():
        execution_order.append(2)
        return True, "verified"

    gate_fns = {1: mock_gate_1, 2: mock_gate_2}

    results = await _execute_gates_loop(
        gate_order=[1, 2], gate_fns=gate_fns, skip=set(), force=set(), fail_fast=False
    )

    assert execution_order == [1, 2]
    assert results[1][0] is True
    assert results[2][0] is True


@pytest.mark.asyncio
async def test_pipeline_fail_fast():
    execution_order = []

    async def mock_gate_1():
        execution_order.append(1)
        return False, "failed"

    async def mock_gate_2():
        execution_order.append(2)
        return True, "verified"

    gate_fns = {1: mock_gate_1, 2: mock_gate_2}

    results = await _execute_gates_loop(
        gate_order=[1, 2], gate_fns=gate_fns, skip=set(), force=set(), fail_fast=True
    )

    assert execution_order == [1]
    assert results[1][0] is False
    assert 2 not in results


@pytest.mark.asyncio
async def test_pipeline_skip():
    execution_order = []

    async def mock_gate_1():
        execution_order.append(1)
        return True, "verified"

    async def mock_gate_2():
        execution_order.append(2)
        return True, "verified"

    gate_fns = {1: mock_gate_1, 2: mock_gate_2}

    results = await _execute_gates_loop(
        gate_order=[1, 2], gate_fns=gate_fns, skip={1}, force=set(), fail_fast=False
    )

    assert execution_order == [2]
    assert results[1][1] == "skipped"
    assert results[2][0] is True
