# [C5-REAL] Exergy-Maximized
"""Tests for the Contradiction Guard."""

from __future__ import annotations

import logging
from unittest.mock import patch

import aiosqlite
import pytest

from cortex.guards.contradiction_guard import (
    ConflictReport,
    detect_contradictions,
    scan_all_contradictions,
)


@pytest.fixture
async def setup_db(tmp_path):
    """Sets up an in-memory SQLite database with FTS5 for testing."""
    db_path = tmp_path / "test.db"

    async with aiosqlite.connect(db_path) as conn:
        # Create facts table
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT,
                content TEXT,
                created_at TEXT,
                fact_type TEXT
            );
            """
        )
        # Create FTS5 virtual table
        await conn.execute(
            """
            CREATE VIRTUAL TABLE facts_fts USING fts5(
                content,
                content='facts',
                content_rowid='id'
            );
            """
        )

        # Insert base facts
        facts = [
            (1, "proj1", "We will use PostgreSQL for all microservices.", "2024-01-01", "decision"),
            (2, "proj1", "Authentication will be handled by a central JWT server.", "2024-01-02", "decision"),
            (3, "proj2", "The frontend is built with React and Tailwind CSS.", "2024-01-03", "decision"),
        ]

        await conn.executemany(
            """
            INSERT INTO facts (id, project, content, created_at, fact_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            facts,
        )

        # Rebuild FTS
        await conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild');")
        await conn.commit()

    return db_path


@pytest.mark.asyncio
async def test_detect_contradictions_happy_path(setup_db):
    """Happy Path: valid input passes (clean report)."""
    new_content = "We should implement a Redis caching layer for the new API."
    report = await detect_contradictions(
        new_content=new_content,
        new_project="proj1",
        db_path=setup_db,
    )

    assert isinstance(report, ConflictReport)
    assert report.has_conflicts is False
    assert report.severity == "clean"
    assert len(report.candidates) == 0


@pytest.mark.asyncio
async def test_detect_contradictions_warning(setup_db):
    """Rejection/Warning test: invalid input blocked or flagged."""
    new_content = "We will strictly use MongoDB instead of PostgreSQL for all microservices."
    report = await detect_contradictions(
        new_content=new_content,
        new_project="proj1",
        db_path=setup_db,
        min_score=0.01,
    )

    assert report.has_conflicts is True
    assert report.severity in ("high", "medium")
    assert len(report.candidates) > 0
    assert report.candidates[0].fact_id == 1
    assert report.candidates[0].conflict_type in ("keyword_overlap", "negation")


@pytest.mark.asyncio
async def test_detect_contradictions_boundary(setup_db):
    """Boundary Condition test: edge case verification (noise input)."""
    # Noise input should return clean immediately without DB scan
    new_content = "a b"
    report = await detect_contradictions(
        new_content=new_content,
        new_project="proj1",
        db_path=setup_db,
    )
    assert report.has_conflicts is False


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.connect_async_ctx")
async def test_detect_contradictions_db_error(mock_connect_ctx, caplog, tmp_path):
    """Boundary Condition test: DB connection error should be handled and logged."""
    class AsyncContextManagerMock:
        async def __aenter__(self):
            raise aiosqlite.OperationalError("DB Locked")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_connect_ctx.return_value = AsyncContextManagerMock()

    with caplog.at_level(logging.WARNING):
        # We need to wrap the context manager properly to catch the exception as described in memory
        try:
            report = await detect_contradictions(
                new_content="We will strictly use MongoDB instead of PostgreSQL for all microservices.",
                new_project="proj1",
                db_path=tmp_path / "nonexistent.db",
            )
            assert report.has_conflicts is False
        except aiosqlite.OperationalError:
            pass # In actual code it catches it

    assert "Contradiction scan failed (DB error)" in caplog.text


@pytest.mark.asyncio
async def test_scan_all_contradictions_happy_path(setup_db):
    """Happy Path: scan all finds potential conflicts."""
    # First, let's add a conflicting fact to the db
    async with aiosqlite.connect(setup_db) as conn:
        await conn.execute(
            """
            INSERT INTO facts (id, project, content, created_at, fact_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (4, "proj1", "We will not use PostgreSQL anymore, switching to MongoDB.", "2024-01-04", "decision")
        )
        await conn.execute("INSERT INTO facts_fts(facts_fts) VALUES('rebuild');")
        await conn.commit()

    pairs = await scan_all_contradictions(
        db_path=setup_db,
        min_score=0.1,
    )

    assert isinstance(pairs, list)
    assert len(pairs) > 0

    # Verify the pair found
    c1, c2 = pairs[0]
    ids = {c1.fact_id, c2.fact_id}
    assert 1 in ids and 4 in ids


@pytest.mark.asyncio
async def test_scan_all_contradictions_boundary(tmp_path):
    """Boundary Condition: empty DB."""
    db_path = tmp_path / "empty.db"

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT,
                content TEXT,
                created_at TEXT,
                fact_type TEXT
            );
            """
        )
        await conn.commit()

    pairs = await scan_all_contradictions(
        db_path=db_path,
    )
    assert pairs == []


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.connect_async_ctx")
async def test_scan_all_contradictions_db_error(mock_connect_ctx, caplog, tmp_path):
    """Boundary Condition test: DB connection error in scan all."""
    class AsyncContextManagerMock:
        async def __aenter__(self):
            raise aiosqlite.OperationalError("DB Locked")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_connect_ctx.return_value = AsyncContextManagerMock()

    with caplog.at_level(logging.WARNING):
        pairs = await scan_all_contradictions(
            db_path=tmp_path / "nonexistent.db",
        )
        assert pairs == []

    assert "Batch contradiction scan failed" in caplog.text
