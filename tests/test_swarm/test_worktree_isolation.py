# No pyline needed

import pytest

from cortex.extensions.swarm.worktree_isolation import isolated_worktree


@pytest.mark.asyncio
async def test_isolated_worktree_lifecycle(tmp_path):
    """Prueba que el ciclo térmodinámico de creación y limpieza del worktree funciona."""
    # Como esta prueba se corre dentro de cortex que es un repo git válido,
    # la comprobación funcionará
    branch_name = "test/entropy-zero-agent-branch"
    base_target = tmp_path / "worktrees"

    async with isolated_worktree(branch_name, str(base_target)) as worktree_path:
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()  # git worktree pone un archivo .git

        # Test agent mutation
        test_file = worktree_path / "agent_test_mutation.txt"
        test_file.write_text("Sovereign mutation")
        assert test_file.exists()

    # Fuera del context manager, el worktree debió ser aniquilado
    assert not worktree_path.exists()


@pytest.mark.asyncio
async def test_isolated_worktree_exception_cleanup(tmp_path):
    """Garantiza la limpieza Anti-basura O(1) incluso si el agente explota desde dentro."""
    branch_name = "test/entropy-zero-error-branch"
    base_target = tmp_path / "worktrees_err"
    worktree_ref = None

    try:
        async with isolated_worktree(branch_name, str(base_target)) as worktree_path:
            worktree_ref = worktree_path
            assert worktree_path.exists()
            raise ValueError("LLM Hallucination Error")
    except ValueError:
        pass  # Catch the expected error

    # Aniquilación termodinámica confirmada
    assert worktree_ref is not None
    assert not worktree_ref.exists()
