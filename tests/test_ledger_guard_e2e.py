"""
CORTEX-Persist E2E Integration Test
Validates: Guard → Ledger → Taint → Git DAG pipeline.
Uses a throwaway Git repo in /tmp to avoid polluting the real workspace.
"""
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from cortex.guards.admission import NullExergyError, StochasticHallucinationError
from cortex.ledger import GitSovereignLedger


@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary Git repo for test isolation."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "cortex@test.local"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "CORTEX-TEST"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    # Need at least one commit for the DAG to exist
    (tmp_path / ".cortex_genesis").write_text("genesis")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "genesis"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    return tmp_path


# ---------------------------------------------------------------
# Happy path: valid mutation → taint persisted in DAG
# ---------------------------------------------------------------


@pytest.mark.asyncio()
async def test_valid_mutation_persists_taint(tmp_git_repo: Path) -> None:
    ledger = GitSovereignLedger(workspace_root=str(tmp_git_repo))

    payload = {
        "action": "crystallize",
        "value": str(Decimal("42.5")),  # String, NOT float
        "epoch": 1,
    }

    tainted = await ledger.commit_state(
        state_mutation=payload,
        file_name="test_entry.json",
        commit_message="E2E: valid mutation",
    )

    assert tainted is not None
    assert len(tainted.taint) == 64  # SHA-256 hex

    # Verify the commit message contains the taint prefix
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        cwd=tmp_git_repo, capture_output=True, text=True, check=True,
    )
    assert tainted.taint[:12] in result.stdout


# ---------------------------------------------------------------
# Guard rejection: float in payload → StochasticHallucinationError
# ---------------------------------------------------------------


@pytest.mark.asyncio()
async def test_float_payload_rejected_by_guard(tmp_git_repo: Path) -> None:
    ledger = GitSovereignLedger(workspace_root=str(tmp_git_repo))

    payload = {
        "action": "corrupt",
        "value": 3.14,  # FLOAT → Byzantine violation
    }

    with pytest.raises(StochasticHallucinationError):
        await ledger.commit_state(state_mutation=payload)


# ---------------------------------------------------------------
# Guard rejection: empty payload → NullExergyError
# ---------------------------------------------------------------


@pytest.mark.asyncio()
async def test_empty_payload_rejected_by_guard(tmp_git_repo: Path) -> None:
    ledger = GitSovereignLedger(workspace_root=str(tmp_git_repo))

    with pytest.raises(NullExergyError):
        await ledger.commit_state(state_mutation={})
