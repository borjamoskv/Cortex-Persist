import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from babylon60.mcts.git_env import MCTSGitEnvironment


@pytest.fixture
def mock_router():
    return MagicMock()


@pytest.mark.asyncio
async def test_secure_checkout_concurrency(mock_router, tmp_path):
    """
    Test that secure_checkout can safely run concurrently under BFT contention,
    and properly tears down the worktree and the ephemeral branch.
    """
    # Initialize the Git environment
    target_file = tmp_path / "dummy.py"
    target_file.touch()

    # We create a dummy .git so the init path resolution works
    (tmp_path / ".git").mkdir()

    env = MCTSGitEnvironment(router=mock_router, target_file=target_file)

    # Mock create_subprocess_shell
    # We will track which commands are called
    executed_commands = []

    async def mock_create_subprocess_shell(cmd, *args, **kwargs):
        executed_commands.append(cmd)

        # Return a mock process
        mock_proc = MagicMock()
        from unittest.mock import AsyncMock

        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0
        return mock_proc

    with patch(
        "cortex.mcts.git_env.asyncio.create_subprocess_shell",
        side_effect=mock_create_subprocess_shell,
    ):
        # Simulate highly concurrent BFT cleanup (e.g. 5 branches rolling back at once)
        nodes_to_cleanup = [f"BFT-{i}" for i in range(5)]

        await asyncio.gather(*(env.secure_checkout(node_id) for node_id in nodes_to_cleanup))

        # Verify that all commands were dispatched correctly
        # Each node should have 1 worktree remove and 1 branch -D
        assert len(executed_commands) == 10

        for node_id in nodes_to_cleanup:
            expected_wt_path = env._get_worktree_path(node_id)
            expected_branch = f"chronos/node-{node_id}"

            # Check worktree removal
            assert any(
                f"git worktree remove --force {expected_wt_path}" in cmd
                for cmd in executed_commands
            )
            # Check branch deletion
            assert any(f"git branch -D {expected_branch}" in cmd for cmd in executed_commands)


@pytest.mark.asyncio
async def test_branch_out(mock_router, tmp_path):
    target_file = tmp_path / "dummy.py"
    target_file.touch()
    (tmp_path / ".git").mkdir()

    env = MCTSGitEnvironment(router=mock_router, target_file=target_file)
    executed_commands = []

    async def mock_create_subprocess_shell(cmd, *args, **kwargs):
        executed_commands.append(cmd)
        mock_proc = MagicMock()
        from unittest.mock import AsyncMock

        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0
        return mock_proc

    with patch(
        "cortex.mcts.git_env.asyncio.create_subprocess_shell",
        side_effect=mock_create_subprocess_shell,
    ):
        branch_name = await env.branch_out("main", "XYZ-123")
        assert branch_name == "chronos/node-XYZ-123"
        assert len(executed_commands) == 2

        assert any(f"git branch {branch_name} main" in cmd for cmd in executed_commands)
        assert any("git worktree add" in cmd and branch_name in cmd for cmd in executed_commands)


@pytest.mark.asyncio
async def test_prune_orphans_recovers_anergy(mock_router, tmp_path):
    """
    Test that prune_orphans safely deletes orphaned worktrees and branches.
    """
    # Initialize the Git environment
    target_file = tmp_path / "dummy.py"
    target_file.touch()

    (tmp_path / ".git").mkdir()

    env = MCTSGitEnvironment(router=mock_router, target_file=target_file)

    # Create mock orphaned worktrees
    wt1 = env.worktrees_dir / "node-orphan-1"
    wt2 = env.worktrees_dir / "node-orphan-2"
    wt1.mkdir(parents=True)
    wt2.mkdir(parents=True)

    executed_commands = []

    async def mock_create_subprocess_shell(cmd, *args, **kwargs):
        executed_commands.append(cmd)

        mock_proc = MagicMock()
        from unittest.mock import AsyncMock

        if "branch --list" in cmd:
            mock_proc.communicate = AsyncMock(
                return_value=(b"chronos/node-orphan-1\n  chronos/node-orphan-2\n", b"")
            )
        else:
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        mock_proc.returncode = 0
        return mock_proc

    with patch(
        "cortex.mcts.git_env.asyncio.create_subprocess_shell",
        side_effect=mock_create_subprocess_shell,
    ):
        metrics = await env.prune_orphans()

        # Verify commands were executed
        assert any(f"git worktree remove --force {wt1}" in cmd for cmd in executed_commands)
        assert any("git branch -D chronos/node-orphan-1" in cmd for cmd in executed_commands)

        # Verify metrics
        assert metrics["worktrees_removed"] == 2
        assert metrics["branches_removed"] == 2

        # Verify that rm -rf was called by checking if directories exist
        assert not wt1.exists()
        assert not wt2.exists()
