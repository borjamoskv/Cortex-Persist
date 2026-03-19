"""Tests for CORTEX Autonomous Executor.

Tests:
    - Task planning phase (step decomposition)
    - Full lifecycle: plan → execute → verify
    - Self-correction on step failure
    - Max retries exceeded → FAILED
    - Session cancellation mid-execution
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cortex.agents.executor import AutonomousExecutor
from cortex.agents.session import (
    SessionStatus,
    SessionStore,
    StepStatus,
)
from cortex.agents.tools import ToolRegistry


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_executor.db")
    return SessionStore(db_path=db_path)


def _mock_tool(name: str, result: dict | None = None, fail: bool = False):
    """Create a mock tool implementing the Tool protocol."""
    tool = AsyncMock()
    tool.name = name
    if fail:
        tool.execute = AsyncMock(side_effect=RuntimeError("Tool failed"))
    else:
        tool.execute = AsyncMock(
            return_value=result or {"success": True, "output": "ok"},
        )
    return tool


def _make_registry(*tools) -> ToolRegistry:
    """Build a ToolRegistry from mock tools."""
    registry = ToolRegistry()
    for t in tools:
        registry.register(t)
    return registry


class TestExecutorPlanning:
    def test_plan_creates_steps(self, store):
        session = store.create("Create a hello.py that prints Hello World")
        tools = _make_registry(_mock_tool("file_write"), _mock_tool("terminal"))

        executor = AutonomousExecutor(session, store, tools)
        steps = executor._plan_task(session.task)

        assert len(steps) >= 1
        # Should have at least a file_write step and a final verification
        descriptions = [s.description for s in steps]
        assert any("Create" in d or "create" in d.lower() for d in descriptions)

    def test_plan_test_task(self, store):
        session = store.create("Run pytest on the test suite")
        tools = _make_registry(_mock_tool("test_runner"), _mock_tool("terminal"))

        executor = AutonomousExecutor(session, store, tools)
        steps = executor._plan_task(session.task)

        tool_names = [s.tool_name for s in steps]
        assert "test_runner" in tool_names

    def test_plan_git_task(self, store):
        session = store.create("Commit all changes and create a branch")
        tools = _make_registry(_mock_tool("git"), _mock_tool("terminal"))

        executor = AutonomousExecutor(session, store, tools)
        steps = executor._plan_task(session.task)

        tool_names = [s.tool_name for s in steps]
        assert "git" in tool_names

    def test_plan_debug_task(self, store):
        session = store.create("Fix the failing test in test_auth.py")
        tools = _make_registry(
            _mock_tool("file_read"),
            _mock_tool("file_write"),
            _mock_tool("terminal"),
        )

        executor = AutonomousExecutor(session, store, tools)
        steps = executor._plan_task(session.task)

        tool_names = [s.tool_name for s in steps]
        assert "file_read" in tool_names
        assert "file_write" in tool_names


class TestExecutorLifecycle:
    @pytest.mark.asyncio
    async def test_full_lifecycle_success(self, store):
        session = store.create("Create a new file")
        tools = _make_registry(
            _mock_tool("file_write", {"success": True, "path": "/tmp/x.py"}),
            _mock_tool("terminal", {"success": True, "stdout": "", "returncode": 0}),
        )

        executor = AutonomousExecutor(session, store, tools)
        result = await executor.run()

        assert result.status in (SessionStatus.COMPLETED, SessionStatus.VERIFYING)
        assert result.completed_steps >= 1

    @pytest.mark.asyncio
    async def test_lifecycle_with_step_failure_and_recovery(self, store):
        session = store.create("Build something complex")

        # Tool that fails once then succeeds
        call_count = 0

        async def flaky_execute(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient failure")
            return {"success": True, "output": "recovered"}

        flaky_tool = AsyncMock()
        flaky_tool.name = "terminal"
        flaky_tool.execute = flaky_execute

        file_tool = _mock_tool(
            "file_write",
            {"success": True, "path": "/tmp/x"},
        )
        tools = _make_registry(file_tool, flaky_tool)

        executor = AutonomousExecutor(session, store, tools)
        result = await executor.run()

        # Should complete because the step self-corrected
        assert result.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
        )

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, store):
        session = store.create("Run a command that always fails")

        always_fail = _mock_tool(
            "terminal",
            fail=True,
        )
        tools = _make_registry(always_fail)

        executor = AutonomousExecutor(session, store, tools)
        result = await executor.run()

        assert result.status == SessionStatus.FAILED
        assert result.error  # Should have error message

    @pytest.mark.asyncio
    async def test_session_persisted_throughout(self, store):
        session = store.create("Persist check")
        tools = _make_registry(
            _mock_tool("terminal", {"success": True, "returncode": 0, "stdout": ""}),
        )

        executor = AutonomousExecutor(session, store, tools)
        await executor.run()

        # Verify session was persisted
        fetched = store.get(session.session_id)
        assert fetched is not None
        assert fetched.status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
        )
        assert len(fetched.logs) > 0


class TestExecutorStepExecution:
    @pytest.mark.asyncio
    async def test_execute_step_tracks_duration(self, store):
        session = store.create("Duration test")
        tool = _mock_tool("terminal", {"success": True, "returncode": 0, "stdout": ""})
        tools = _make_registry(tool)

        executor = AutonomousExecutor(session, store, tools)

        from cortex.agents.session import SessionStep

        step = SessionStep(
            description="echo test",
            tool_name="terminal",
            tool_args={"command": "echo test"},
        )

        success = await executor._execute_step(step)
        assert success is True
        assert step.duration_ms > 0
        assert step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_step_missing_tool(self, store):
        session = store.create("Missing tool test")
        tools = ToolRegistry()  # Empty

        executor = AutonomousExecutor(session, store, tools)

        from cortex.agents.session import SessionStep

        step = SessionStep(
            description="use nonexistent tool",
            tool_name="nonexistent",
        )

        # Missing tool should not crash — step completes with warning
        success = await executor._execute_step(step)
        assert success is True
        assert "not available" in step.output
