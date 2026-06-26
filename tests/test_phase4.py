# [C5-REAL] Exergy-Maximized

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from cortex_extensions.aether.tools import AgentToolkit
from cortex_extensions.swarm.auto_fix import AutoFixPipeline


@pytest.fixture
def temp_repo(tmp_path):
    """Create a dummy git repo for testing merges."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "master"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@cortex.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    (repo / "README.md").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "[bridge] initial commit"], cwd=repo, check=True)
    return repo


# ── 1. Tool Sealing Tests (Ω₃) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_toolkit_sealing_allowed(tmp_path):
    """Verify that allowed tools dispatch correctly."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=["read_file"])

    # Mock read_file to avoid actual IO
    toolkit.read_file = MagicMock(return_value="content")

    result = await toolkit.dispatch("read_file", {"path": "foo.py"})
    assert result == "content"
    toolkit.read_file.assert_called_once()


@pytest.mark.asyncio
async def test_toolkit_sealing_blocked(tmp_path):
    """Verify that unauthorized tools are intercepted."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=["read_file"])

    # Try to dispatch 'bash', which is NOT in allowed_tools
    result = await toolkit.dispatch("bash", {"cmd": "ls"})
    assert "ToolNotAllowedError" in result
    assert "bash" in result


def test_toolkit_expansion(tmp_path):
    """Verify high-level capability expansion."""
    # 'filesystem' should expand to read_file, write_file, list_dir
    toolkit = AgentToolkit(tmp_path, allowed_tools=["filesystem"])

    assert "read_file" in toolkit.allowed_tools
    assert "write_file" in toolkit.allowed_tools
    assert "list_dir" in toolkit.allowed_tools
    assert "bash" not in toolkit.allowed_tools


@pytest.mark.asyncio
async def test_toolkit_unrestricted_by_default(tmp_path):
    """Verify that if allowed_tools is None, everything is allowed (legacy)."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=None)
    toolkit.read_file = MagicMock(return_value="content")

    result = await toolkit.dispatch("read_file", {"path": "foo.py"})
    assert result == "content"


# ── 2. Autonomous Merge Tests (Ω₂) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_autonomous_merge_success(temp_repo):
    """Test successful fast-forward merge (Ω₂)."""
    import subprocess

    repo_path = temp_repo

    # Create a branch and a commit
    branch = "fix/ghost-1"
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True)
    (repo_path / "fix.txt").write_text("fix")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "[bridge] fix commit"], cwd=repo_path, check=True)

    # Go back to master
    subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

    pipeline = AutoFixPipeline(repo_path=str(repo_path))
    success = await pipeline._autonomous_merge(branch)

    assert success is True
    # Verify merge happened
    assert (repo_path / "fix.txt").exists()
    # Verify branch was deleted
    res = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
    assert branch not in res.stdout


@pytest.mark.asyncio
async def test_autonomous_merge_failure_conflict(temp_repo):
    """Test merge failure when not fast-forwardable."""
    import subprocess

    repo_path = temp_repo

    # 1. Create branch and commit
    branch = "fix/conflict"
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True)
    (repo_path / "file.txt").write_text("line A")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "[bridge] commit A"], cwd=repo_path, check=True)

    # 2. Go to master and create a conflicting commit
    subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)
    (repo_path / "file.txt").write_text("line B")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "[bridge] commit B"], cwd=repo_path, check=True)

    pipeline = AutoFixPipeline(repo_path=str(repo_path))
    # This should fail because it's not a fast-forward merge
    success = await pipeline._autonomous_merge(branch)

    assert success is False
    # Verify branch still exists
    res = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
    assert branch in res.stdout


@pytest.mark.asyncio
@patch("cortex_extensions.swarm.auto_fix.AutoFixPipeline._execute")
@patch("cortex_extensions.swarm.auto_fix.AutoFixPipeline._autonomous_merge")
async def test_process_ghost_triggers_merge(mock_merge, mock_execute):
    """Verify that process_ghost calls _autonomous_merge on success."""
    mock_execute.return_value = {
        "status": "done",
        "branch": "autofix/ghost-123",
        "summary": "Fix applied",
        "error": "",
        "tests_passed": True,
    }
    mock_merge.return_value = True

    pipeline = AutoFixPipeline()

    @dataclass
    class MockGhost:
        id: str = "123"
        description: str = "TypeError"
        project: str = "CORTEX"

    result = await pipeline.process_ghost(MockGhost())

    assert result.success is True
    mock_merge.assert_called_once_with("autofix/ghost-123")
    assert "Merged to main" in result.summary


@pytest.mark.asyncio
async def test_hooked_tool_execution_timeout():
    """Verify that hooked_tool_execution enforces the timeout limit."""
    import time
    import asyncio
    from cortex_extensions.aether.hooks import hooked_tool_execution

    @hooked_tool_execution(timeout_limit=0.1)
    async def async_slow_tool():
        await asyncio.sleep(0.5)
        return "ok"

    @hooked_tool_execution(timeout_limit=0.1)
    def sync_slow_tool():
        time.sleep(0.5)
        return "ok"

    @hooked_tool_execution(timeout_limit=0.5)
    async def async_fast_tool():
        return "fast_async"

    @hooked_tool_execution(timeout_limit=0.5)
    def sync_fast_tool():
        return "fast_sync"

    res_async_slow = await async_slow_tool()
    assert "[ERROR]" in res_async_slow
    assert "timed out after 0.1 seconds" in res_async_slow

    res_sync_slow = await sync_slow_tool()
    assert "[ERROR]" in res_sync_slow
    assert "timed out after 0.1 seconds" in res_sync_slow

    res_async_fast = await async_fast_tool()
    assert res_async_fast == "fast_async"

    res_sync_fast = await sync_fast_tool()
    assert res_sync_fast == "fast_sync"


@pytest.mark.asyncio
async def test_evolution_supervisor_multipass_loop():
    """Verify that EvolutionSupervisor executes the multipass loop with pre/post-eval."""
    from cortex.agents.supervisor import EvolutionSupervisor
    from cortex.agents.base import BaseAgent
    from cortex.agents.manifest import AgentManifest

    # Create dummy agent
    manifest = AgentManifest(
        agent_id="test-evo-agent",
        purpose="testing",
        tools_allowed=[],
        can_delegate=False,
        daemon=False,
    )

    # We mock BaseAgent and add a execute_objective method
    class MockAutonomousAgent(BaseAgent):
        def __init__(self, manifest, bus):
            super().__init__(manifest, bus)
            self.execution_count = 0

        async def execute_objective(self, objective: str) -> dict:
            self.execution_count += 1
            if self.execution_count >= 2:
                return {"status": "SUCCESS", "info": "achieved"}
            return {"status": "FAILED", "info": "not yet"}

    bus = MagicMock()
    agent = MockAutonomousAgent(manifest, bus)

    supervisor = EvolutionSupervisor()
    supervisor.register(agent)

    # Pre-eval and Post-eval mocks
    pre_eval_mock = MagicMock(return_value={"pre_metric": 42})
    post_eval_mock = MagicMock(
        side_effect=[{"success": False, "score": 0.5}, {"success": True, "score": 1.0}]
    )

    # Mock Dream Engine
    dream_engine_mock = MagicMock()

    class DummyDreamResult:
        clusters_found = 3
        bridges_created = 5
        engrams_reweighted = 2
        duration_ms = 120.0

    # Make dream_cycle an async mock
    async def dummy_dream_cycle(tenant_id):
        return DummyDreamResult()

    dream_engine_mock.dream_cycle = dummy_dream_cycle

    res = await supervisor.run_autonomous_loop(
        agent_id="test-evo-agent",
        objective="Self-Improve",
        pre_eval=pre_eval_mock,
        post_eval=post_eval_mock,
        max_passes=3,
        dream_engine=dream_engine_mock,
    )

    assert res["status"] == "SUCCESS"
    assert res["passes_executed"] == 2
    assert agent.execution_count == 2
    assert pre_eval_mock.call_count == 2
    assert post_eval_mock.call_count == 2

    dream_int = res["dream_integration"]
    assert dream_int["status"] == "COMPLETED"
    assert dream_int["clusters_found"] == 3
    assert dream_int["bridges_created"] == 5
