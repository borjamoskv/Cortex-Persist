import pytest
import aiosqlite
from unittest.mock import patch

from cortex.guards.contradiction_guard.detector import _fetch_decision_rows, detect_contradictions


@pytest.fixture
async def in_memory_db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                project TEXT,
                content TEXT,
                created_at TEXT,
                fact_type TEXT
            )
            """
        )
        await conn.execute(
            """
            CREATE VIRTUAL TABLE facts_fts USING fts5(
                content,
                content='facts',
                content_rowid='id'
            )
            """
        )
        # Add a trigger to keep fts updated for easy testing
        await conn.execute(
            """
            CREATE TRIGGER facts_ai AFTER INSERT ON facts BEGIN
                INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
            END;
            """
        )

        # Insert some test data
        await conn.execute(
            "INSERT INTO facts (project, content, created_at, fact_type) VALUES (?, ?, ?, ?)",
            ("TestProj", "This is an old decision about using python.", "2023-01-01", "decision"),
        )
        await conn.execute(
            "INSERT INTO facts (project, content, created_at, fact_type) VALUES (?, ?, ?, ?)",
            ("TestProj", "We decided to not use java.", "2023-01-02", "decision"),
        )
        await conn.execute(
            "INSERT INTO facts (project, content, created_at, fact_type) VALUES (?, ?, ?, ?)",
            ("OtherProj", "Python is good.", "2023-01-03", "decision"),
        )
        await conn.execute(
            "INSERT INTO facts (project, content, created_at, fact_type) VALUES (?, ?, ?, ?)",
            ("TestProj", "Just a normal fact.", "2023-01-04", "other"),
        )

        await conn.commit()
        yield conn


@pytest.mark.asyncio
async def test_fetch_decision_rows_fts(in_memory_db):
    tokens = {"python"}
    rows = await _fetch_decision_rows(in_memory_db, tokens, "TestProj", use_fts=True)
    assert len(rows) == 2
    contents = [r["content"] for r in rows]
    assert "This is an old decision about using python." in contents
    assert "Python is good." in contents


@pytest.mark.asyncio
async def test_fetch_decision_rows_no_fts(in_memory_db):
    tokens = {"python"}
    rows = await _fetch_decision_rows(in_memory_db, tokens, "TestProj", use_fts=False)
    # Should fetch all 3 decisions, sorted by project matches first
    assert len(rows) == 3
    assert rows[0]["project"] == "TestProj"


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.detector.connect_async_ctx")
async def test_detect_contradictions(mock_connect_ctx, in_memory_db):
    # Mock context manager to return our in_memory_db
    mock_connect_ctx.return_value.__aenter__.return_value = in_memory_db

    # "python" overlaps with the first decision
    report = await detect_contradictions(
        "We are using python in our new project.", "TestProj", db_path=":memory:"
    )

    assert report.has_conflicts
    assert report.new_project == "TestProj"
    assert len(report.candidates) > 0
    assert any("python" in c.content.lower() for c in report.candidates)


@pytest.mark.asyncio
async def test_detect_contradictions_noise():
    report = await detect_contradictions("MAILTV-1: ARCHIVE using python.", "TestProj")
    assert not report.has_conflicts


@pytest.mark.asyncio
async def test_detect_contradictions_few_tokens():
    report = await detect_contradictions(
        "is a the",  # all stop words -> 0 tokens
        "TestProj",
    )
    assert not report.has_conflicts


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.detector.connect_async_ctx")
async def test_detect_contradictions_db_error(mock_connect_ctx):
    # Setup mock to raise OperationalError
    mock_connect_ctx.return_value.__aenter__.side_effect = aiosqlite.OperationalError()

    report = await detect_contradictions("We are using python.", "TestProj", db_path=":memory:")
    # Should handle gracefully and return empty report
    assert not report.has_conflicts
