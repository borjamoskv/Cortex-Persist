import json
import sqlite3

import pytest

from cortex.engine.reporter import ManifoldStatus, SovereignReporter


@pytest.fixture
def mock_db(tmp_path) -> str:
    """Creates a temporary SQLite database mimicking the CORTEX structure."""
    db_path = str(tmp_path / "cortex_test.db")
    with sqlite3.connect(db_path) as conn:
        # Create minimal causal_edges table
        conn.execute(
            """
            CREATE TABLE causal_edges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id     INTEGER NOT NULL,
                parent_id   INTEGER,
                signal_id   INTEGER,
                edge_type   TEXT NOT NULL DEFAULT 'triggered_by',
                project     TEXT,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "INSERT INTO causal_edges (fact_id, edge_type) VALUES (1, 'test'), (2, 'test')"
        )

        # Create minimal signals table
        conn.execute(
            """
            CREATE TABLE signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                payload     TEXT NOT NULL DEFAULT '{}',
                source      TEXT NOT NULL,
                project     TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                consumed_by TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.execute(
            "INSERT INTO signals (event_type, source, consumed_by) VALUES (?, ?, ?), (?, ?, ?)",
            ("sig1", "cli", "[]", "sig2", "agent", '["a"]'),
        )

        # Create minimal facts table
        conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                fact_type TEXT,
                source TEXT,
                content TEXT,
                meta TEXT,
                created_at TEXT
            )
            """
        )
        # Add 1 ghost fact
        conn.execute("INSERT INTO facts (fact_type) VALUES ('ghost')")

        # Add 2 knowledge/chronos-roi facts
        roi_meta = json.dumps({"hours_saved": 42.0, "roi_ratio": 3.14})
        conn.execute(
            "INSERT INTO facts (fact_type, source, content, meta, created_at) "
            "VALUES ('knowledge', 'chronos-roi', 'summary', ?, '2026-01-01')",
            (roi_meta,),
        )
        conn.execute(
            "INSERT INTO facts (fact_type, source, content, meta, created_at) "
            "VALUES ('knowledge', 'chronos-roi', 'summary', ?, '2026-01-02')",
            (roi_meta,),
        )

    return db_path


@pytest.mark.asyncio
async def test_collect_metrics(mock_db: str):
    """Test that SovereignReporter correctly aggregates ManifoldStatus."""
    reporter = SovereignReporter(mock_db, project="test_proto")
    status: ManifoldStatus = await reporter.collect_metrics()

    assert status.project == "test_proto"
    assert status.active_ghosts == 1

    # We inserted 2 edges in a DB of 3 facts (2 roi, 1 ghost).
    # Integrity = (2 edges / 3 facts) * 100 = 66.67
    assert status.architecture_integrity == pytest.approx(66.67, 0.1)

    # Efficiency logic checks
    assert status.efficiency["history_count"] == 2
    assert status.efficiency["latest_roi"]["hours_saved"] == 42.0

    assert isinstance(status.timestamp, str)
    assert len(status.timestamp) > 10


@pytest.mark.asyncio
async def test_missing_db_raises_error(tmp_path):
    """Ensure proper exception handling when DB is missing."""
    invalid_path = str(tmp_path / "nonexistent.db")
    reporter = SovereignReporter(invalid_path)

    with pytest.raises(sqlite3.OperationalError):
        await reporter.collect_metrics()
