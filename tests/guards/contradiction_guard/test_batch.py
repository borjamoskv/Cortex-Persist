import pytest
import aiosqlite
from unittest.mock import patch

from cortex.guards.contradiction_guard.batch import (
    scan_all_contradictions,
    _process_token_bucket,
    _compare_decisions,
    _prepare_decisions,
    _build_token_index,
)


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

        # Insert test data that should have overlap
        await conn.execute(
            "INSERT INTO facts (id, project, content, created_at, fact_type) VALUES (?, ?, ?, ?, ?)",
            (
                1,
                "TestProj",
                "We decided to build this using python and django.",
                "2023-01-01",
                "decision",
            ),
        )
        await conn.execute(
            "INSERT INTO facts (id, project, content, created_at, fact_type) VALUES (?, ?, ?, ?, ?)",
            (
                2,
                "TestProj",
                "We are building this with python and django because it is fast.",
                "2023-01-02",
                "decision",
            ),
        )
        await conn.execute(
            "INSERT INTO facts (id, project, content, created_at, fact_type) VALUES (?, ?, ?, ?, ?)",
            (3, "OtherProj", "Something completely unrelated.", "2023-01-03", "decision"),
        )

        await conn.commit()
        yield conn


def test_prepare_decisions():
    # Mock row to test _prepare_decisions
    class MockRow(dict):
        pass

    rows = [
        MockRow(
            {
                "id": 1,
                "project": "P1",
                "content": "MAILTV-1: ARCHIVE noise",
                "created_at": "2023-01-01",
            }
        ),
        MockRow(
            {
                "id": 2,
                "project": "P1",
                "content": "Valid decision about python",
                "created_at": "2023-01-01",
            }
        ),
        MockRow({"id": 3, "project": "P1", "content": "short", "created_at": "2023-01-01"}),
    ]

    # Should filter out noise and short decisions
    decisions = _prepare_decisions(rows, None)
    assert len(decisions) == 1
    assert decisions[0]["id"] == 2
    assert "python" in decisions[0]["tokens"]


def test_build_token_index():
    group = [
        {"id": 1, "tokens": {"python", "django"}},
        {"id": 2, "tokens": {"python", "flask"}},
        {"id": 3, "tokens": {"java", "spring"}},
    ]

    index = _build_token_index(group)
    assert 0 in index["python"]
    assert 1 in index["python"]
    assert 2 not in index["python"]
    assert 2 in index["java"]


def test_compare_decisions():
    a = {
        "id": 1,
        "project": "P1",
        "content": "Old decision python",
        "date": "2023-01-01",
        "tokens": {"old", "decision", "python"},
    }
    b = {
        "id": 2,
        "project": "P1",
        "content": "New decision python",
        "date": "2023-01-02",
        "tokens": {"new", "decision", "python"},
    }

    # Same project, matching tokens (decision, python)
    # Jaccard = 2 / 4 = 0.5
    res = _compare_decisions(a, b, min_score=0.1)
    assert res is not None
    score, ca, cb = res
    assert score == 0.5
    assert ca.conflict_type == "keyword_overlap"


def test_compare_decisions_negation():
    a = {
        "id": 1,
        "project": "P1",
        "content": "Use python",
        "date": "2023-01-01",
        "tokens": {"use", "python"},
    }
    b = {
        "id": 2,
        "project": "P1",
        "content": "Never use python",
        "date": "2023-01-02",
        "tokens": {"never", "use", "python"},
    }

    res = _compare_decisions(a, b, min_score=0.1)
    assert res is not None
    score, ca, cb = res
    assert ca.conflict_type == "negation"
    # base jaccard = 2/3 = 0.666...
    # negation mult = 1.3
    # final score = min(1.0, 0.666 * 1.3)
    assert score == pytest.approx(min((2 / 3) * 1.3, 1.0))


def test_process_token_bucket():
    group = [
        {
            "id": 1,
            "project": "P1",
            "content": "Use python",
            "date": "2023-01-01",
            "tokens": {"use", "python"},
        },
        {
            "id": 2,
            "project": "P1",
            "content": "Also use python",
            "date": "2023-01-02",
            "tokens": {"also", "use", "python"},
        },
    ]
    indices = [0, 1]
    seen_pairs = set()
    pairs = []

    _process_token_bucket(indices, group, seen_pairs, pairs, min_score=0.1)

    assert len(pairs) == 1
    assert len(seen_pairs) == 1
    assert (1, 2) in seen_pairs


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.batch.connect_async_ctx")
async def test_scan_all_contradictions(mock_connect_ctx, in_memory_db):
    mock_connect_ctx.return_value.__aenter__.return_value = in_memory_db

    pairs = await scan_all_contradictions(db_path=":memory:", min_score=0.2)

    assert len(pairs) == 1
    a, b = pairs[0]
    # Expect facts 1 and 2 to conflict
    ids = {a.fact_id, b.fact_id}
    assert 1 in ids
    assert 2 in ids


@pytest.mark.asyncio
@patch("cortex.guards.contradiction_guard.batch.connect_async_ctx")
async def test_scan_all_contradictions_error(mock_connect_ctx):
    mock_connect_ctx.return_value.__aenter__.side_effect = aiosqlite.OperationalError()
    pairs = await scan_all_contradictions(db_path=":memory:")
    assert len(pairs) == 0
