"""Tests for Phase 4: Strict Tool Sealing & Autonomous Merge (Ω₂, Ω₃)."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from cortex.extensions.aether.tools import AgentToolkit
from cortex.extensions.swarm.auto_fix import AutoFixPipeline


@pytest.fixture
def temp_repo(tmp_path):
    """Create a dummy git repo for testing merges."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@cortex.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    (repo / "README.md").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo, check=True)
    return repo


# ── 1. Tool Sealing Tests (Ω₃) ─────────────────────────────────────────


def test_toolkit_sealing_allowed(tmp_path):
    """Verify that allowed tools dispatch correctly."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=["read_file"])

    # Mock read_file to avoid actual IO
    toolkit.read_file = MagicMock(return_value="content")

    result = toolkit.dispatch("read_file", {"path": "foo.py"})
    assert result == "content"
    toolkit.read_file.assert_called_once()


def test_toolkit_sealing_blocked(tmp_path):
    """Verify that unauthorized tools are intercepted."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=["read_file"])

    # Try to dispatch 'bash', which is NOT in allowed_tools
    result = toolkit.dispatch("bash", {"cmd": "ls"})
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


def test_toolkit_unrestricted_by_default(tmp_path):
    """Verify that if allowed_tools is None, everything is allowed (legacy)."""
    toolkit = AgentToolkit(tmp_path, allowed_tools=None)
    toolkit.read_file = MagicMock(return_value="content")

    result = toolkit.dispatch("read_file", {"path": "foo.py"})
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
    subprocess.run(["git", "commit", "-m", "fix commit"], cwd=repo_path, check=True)

    # Go back to master
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)

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
    subprocess.run(["git", "commit", "-m", "commit A"], cwd=repo_path, check=True)

    # 2. Go to master and create a conflicting commit
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)
    (repo_path / "file.txt").write_text("line B")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "commit B"], cwd=repo_path, check=True)

    pipeline = AutoFixPipeline(repo_path=str(repo_path))
    # This should fail because it's not a fast-forward merge
    success = await pipeline._autonomous_merge(branch)

    assert success is False
    # Verify branch still exists
    res = subprocess.run(["git", "branch"], cwd=repo_path, capture_output=True, text=True)
    assert branch in res.stdout


@pytest.mark.asyncio
@patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._execute")
@patch("cortex.extensions.swarm.auto_fix.AutoFixPipeline._autonomous_merge")
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
