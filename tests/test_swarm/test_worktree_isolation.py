# [C5-REAL] Exergy-Maximized
# No pyline needed

import pytest

from cortex.extensions.swarm.worktree_isolation import isolated_worktree


@pytest.mark.asyncio
async def test_isolated_worktree_lifecycle(tmp_path):
    """Tests that the thermodynamic creation and cleanup cycle of the worktree works."""
    # Since this test runs inside cortex which is a valid git repo,
    # the check will work
    branch_name = "test/entropy-zero-agent-branch"
    base_target = tmp_path / "worktrees"

    async with isolated_worktree(branch_name, str(base_target)) as worktree_path:
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()  # git worktree pone un archivo .git

        # Test agent mutation
        test_file = worktree_path / "agent_test_mutation.txt"
        test_file.write_text("Sovereign mutation")
        assert test_file.exists()

    # Outside the context manager, the worktree must have been annihilated
    assert not worktree_path.exists()


@pytest.mark.asyncio
async def test_isolated_worktree_exception_cleanup(tmp_path):
    """Guarantees O(1) Anti-garbage cleanup even if the agent explodes from within."""
    branch_name = "test/entropy-zero-error-branch"
    base_target = tmp_path / "worktrees_err"
    worktree_ref = None

    try:
        async with isolated_worktree(branch_name, str(base_target)) as worktree_path:
            worktree_ref = worktree_path
            assert worktree_path.exists()
            raise ValueError("LLM Hallucination Error")
    except ValueError:
        import logging

    # Catch the expected error

    # Thermodynamic annihilation confirmed
    assert worktree_ref is not None
    assert not worktree_ref.exists()
