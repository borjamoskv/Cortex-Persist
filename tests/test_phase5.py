"""Tests for Phase 5: Ω₆ Siege-Verification (Pathogen Matching)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.aether.models import AgentTask, PlanOutput
from cortex.extensions.aether.runner import AetherAgent


@pytest.fixture
def mock_queue():
    queue = MagicMock()
    queue.update = MagicMock()
    return queue


@pytest.mark.asyncio
async def test_siege_verification_instruction_injection(mock_queue):
    """Verify that AetherAgent injects Ω₆ instructions if repro_test is present."""
    AsyncMock()
    # Mock Planner to return a plan with a repro_test
    planner_mock = AsyncMock()
    planner_mock.plan.return_value = PlanOutput(
        summary="Fix bug",
        steps=["Step 1"],
        files_to_touch=["bug.py"],
        tests_to_run=["pytest"],
        repro_test="pytest tests/repro.py",
    )

    executor_mock = AsyncMock()
    executor_mock.execute.return_value = "Done"

    with (
        patch("cortex.extensions.aether.runner.PlannerAgent", return_value=planner_mock),
        patch("cortex.extensions.aether.runner.ExecutorAgent", return_value=executor_mock),
        patch("cortex.extensions.llm.provider.LLMProvider") as mock_llm_cls,
        patch("cortex.extensions.aether.runner.AgentToolkit") as mock_toolkit,
    ):
        mock_toolkit.return_value.git_create_branch.return_value = "OK"
        mock_toolkit.return_value.bash.return_value = "[FAIL] (exit code: 1) error"
        mock_llm_cls.return_value.close = AsyncMock()

        agent = AetherAgent(llm_provider="openai")
        task = AgentTask(title="Bug", description="Fix it", repo_path="/tmp")

        await agent.run_task(task, mock_queue)

        # Verify that executor was called with Ω₆ instructions
        call_args = executor_mock.execute.call_args[0]
        instruction = call_args[1]
        assert "[Ω₆ MANDATORY]" in instruction
        assert "pytest tests/repro.py" in instruction


@pytest.mark.asyncio
async def test_bash_fail_format():
    """Verify that AgentToolkit.bash returns [FAIL] on non-zero exit."""

    from cortex.extensions.aether.tools import AgentToolkit

    # Create a temp dir for the repo
    repo = Path("/tmp/cortex_test_repro")
    repo.mkdir(exist_ok=True)

    toolkit = AgentToolkit(repo)
    # Run a command that fails
    result = toolkit.bash("ls /non-existent-directory-12345")
    assert "[FAIL]" in result
    assert "exit code" in result
