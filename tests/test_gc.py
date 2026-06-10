# [C5-REAL] Exergy-Maximized
"""Tests for Vector Memory Garbage Collection Pipeline."""

from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock

from cortex.compaction.gc import GarbageCollector


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    # Mock engine.session context manager
    session_mock = AsyncMock()

    class AsyncSessionCtx:
        async def __aenter__(self):
            return session_mock

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    engine.session = MagicMock(return_value=AsyncSessionCtx())
    return engine, session_mock


@pytest.mark.asyncio
async def test_gc_run_no_tombstones(mock_engine):
    engine, session = mock_engine
    # Mock select query returning no rows
    cursor_mock = AsyncMock()
    cursor_mock.fetchall = AsyncMock(return_value=[])
    session.execute = AsyncMock(return_value=cursor_mock)

    gc = GarbageCollector(engine)
    stats = await gc.run_gc(force=True)

    assert stats["status"] == "completed"
    assert stats["deleted_facts"] == 0
    assert stats["deleted_embeddings"] == 0


@pytest.mark.asyncio
async def test_gc_run_with_tombstones(mock_engine):
    engine, session = mock_engine

    # Mock cursor for select queries
    select_cursor = AsyncMock()
    select_cursor.fetchall = AsyncMock(return_value=[(101,), (102,)])

    # Mock cursor for sqlite_master check
    table_cursor = AsyncMock()
    table_cursor.fetchall = AsyncMock(return_value=[("fact_embeddings",), ("pruned_embeddings",)])

    # Side effects for execute
    async def mock_execute(query, *args):
        if "SELECT id FROM facts" in query:
            return select_cursor
        elif "SELECT name FROM sqlite_master" in query:
            return table_cursor
        return AsyncMock()

    session.execute = AsyncMock(side_effect=mock_execute)

    gc = GarbageCollector(engine)
    stats = await gc.run_gc(force=True)

    assert stats["status"] == "completed"
    assert stats["deleted_facts"] == 2
    assert stats["deleted_embeddings"] == 2

    # Verify rollback was not called and commit was
    session.rollback.assert_not_called()
    session.commit.assert_called_once()
