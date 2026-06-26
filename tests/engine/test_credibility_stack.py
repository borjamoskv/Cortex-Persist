# [C5-REAL] Exergy-Maximized

import pytest
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from cortex.engine.uncategorized.credibility_stack import LedgerCredibilityStack


@pytest.mark.asyncio
async def test_ledger_credibility_stack_strike(tmp_path):
    # Set up a mock engine and temporary database directory/file path
    db_path = str(tmp_path / "test_cred_stack.db")

    mock_engine = MagicMock()
    mock_engine._db_path = db_path

    mock_conn = MagicMock()
    mock_cursor = AsyncMock()

    # Mock a list of facts for the project
    mock_cursor.fetchall.return_value = [
        (1, "test_proj", "default", "fact content", "memory", "{}", "2026-05-26T22:00:00Z")
    ]

    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.__aenter__.return_value = mock_cursor
    mock_ctx_mgr.__aexit__ = AsyncMock()
    mock_conn.execute.return_value = mock_ctx_mgr

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__.return_value = mock_conn
    mock_session_ctx.__aexit__ = AsyncMock()

    mock_engine.session.return_value = mock_session_ctx

    stack = LedgerCredibilityStack(mock_engine)

    # Execute full credibility strike
    res = await stack.execute_full_strike(project="test_proj", use_ultrathink=True)

    assert res["project"] == "test_proj"
    assert "merkle_root" in res
    assert "signature" in res
    assert res["replay_validated"] is True

    # Cleanup DB and snapshot directories
    if os.path.exists(db_path):
        os.remove(db_path)
    snap_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "snapshots")
    if os.path.exists(snap_dir):
        shutil.rmtree(snap_dir)
