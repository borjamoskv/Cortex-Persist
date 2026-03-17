"""Epoch 8 — Causal Episode Tracer Verification.

Tests:
1. CausalEpisode model instantiation and entropy_density.
2. CausalTracer.trace_episode() reconstructs a DAG from parent_decision_id chains.
3. CausalTracer.recall_episode() finds and deduplicates episodes by query.
4. ThalamusGate causal saturation check rejects facts past threshold.
"""

import asyncio
import os
import sqlite3
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex.memory.models import CausalEpisode


def test_causal_episode_model():
    """Test CausalEpisode instantiation and entropy_density."""
    ep = CausalEpisode(
        root_fact_id=1,
        fact_chain=[
            {"id": 1, "content": "decision A", "fact_type": "decision", "depth": 0},
            {"id": 2, "content": "ghost from A", "fact_type": "ghost", "depth": 1},
            {"id": 3, "content": "decision B", "fact_type": "decision", "depth": 1},
        ],
        project="test",
        ghost_count=1,
        decision_count=2,
    )
    assert ep.root_fact_id == 1
    assert len(ep.fact_chain) == 3
    # entropy_density = 1 / (1 + 2) = 0.333...
    assert abs(ep.entropy_density - 1 / 3) < 0.01
    print("✅ CausalEpisode model: OK")


def _create_test_db():
    """Create an in-memory SQLite DB with facts table and causal chain."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            fact_type TEXT DEFAULT 'knowledge',
            project TEXT DEFAULT 'test',
            parent_decision_id INTEGER REFERENCES facts(id),
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Insert a causal chain: 1 → 2 → 3, and 1 → 4
    conn.execute(
        "INSERT INTO facts (id, content, fact_type, project, parent_decision_id) "
        "VALUES (1, 'Root decision: deploy v2', 'decision', 'cortex', NULL)"
    )
    conn.execute(
        "INSERT INTO facts (id, content, fact_type, project, parent_decision_id) "
        "VALUES (2, 'Error: DB migration failed', 'ghost', 'cortex', 1)"
    )
    conn.execute(
        "INSERT INTO facts (id, content, fact_type, project, parent_decision_id) "
        "VALUES (3, 'Fix: rollback migration', 'decision', 'cortex', 2)"
    )
    conn.execute(
        "INSERT INTO facts (id, content, fact_type, project, parent_decision_id) "
        "VALUES (4, 'Side-effect: cache invalidated', 'ghost', 'cortex', 1)"
    )
    conn.commit()
    return conn


class AsyncSqliteWrapper:
    """Minimal async wrapper for sync sqlite3 connection (testing only)."""

    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql, params=()):
        cursor = self._conn.execute(sql, params)
        return AsyncCursorWrapper(cursor)

    async def commit(self):
        self._conn.commit()


class AsyncCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    async def fetchall(self):
        return self._cursor.fetchall()

    async def fetchone(self):
        return self._cursor.fetchone()


async def test_trace_episode():
    """Test CausalTracer.trace_episode() reconstructs the full DAG."""
    from cortex.memory.episodic import CausalTracer

    conn = _create_test_db()
    aconn = AsyncSqliteWrapper(conn)
    tracer = CausalTracer(aconn)

    # Trace from leaf node (id=3) — should walk up to root (id=1)
    # then down to get full tree
    episode = await tracer.trace_episode(fact_id=3)

    assert episode.root_fact_id == 1
    assert episode.project == "cortex"
    assert episode.depth >= 2  # At least 2 levels deep
    assert episode.ghost_count == 2  # id=2 and id=4
    assert episode.decision_count == 2  # id=1 and id=3
    assert len(episode.fact_chain) == 4  # All 4 facts in the tree
    print(
        f"✅ trace_episode: DAG with {len(episode.fact_chain)} nodes, "
        f"depth={episode.depth}, entropy={episode.entropy_density:.2f}"
    )
    print(f"   Summary:\n{episode.summary}")


async def test_recall_episode():
    """Test CausalTracer.recall_episode() finds episodes by query."""
    from cortex.memory.episodic import CausalTracer

    conn = _create_test_db()
    aconn = AsyncSqliteWrapper(conn)
    tracer = CausalTracer(aconn)

    episodes = await tracer.recall_episode("migration", project="cortex")
    assert len(episodes) >= 1
    # The episode should contain the full chain from root
    ep = episodes[0]
    assert ep.root_fact_id == 1
    assert len(ep.fact_chain) == 4
    print(f"✅ recall_episode: Found {len(episodes)} episode(s) for query 'migration'")


async def test_thalamus_causal_saturation():
    """Test ThalamusGate rejects facts past causal saturation threshold."""
    conn = _create_test_db()
    # Insert 10+ children for parent_id=1 with same fact_type
    for i in range(5, 16):
        conn.execute(
            "INSERT INTO facts (id, content, fact_type, project, parent_decision_id) "
            f"VALUES ({i}, 'child ghost #{i}', 'ghost', 'cortex', 1)"
        )
    conn.commit()
    aconn = AsyncSqliteWrapper(conn)

    from cortex.memory.thalamus import ThalamusGate

    # Create a minimal mock manager
    class MockManager:
        pass

    gate = ThalamusGate(MockManager(), max_causal_children=10)

    # Should be rejected: parent_id=1 has 13 ghost children (id=2,4,5-15)
    should_process, action, meta = await gate.filter(
        content="Yet another ghost from root decision",
        project_id="cortex",
        tenant_id="default",
        fact_type="ghost",
        parent_decision_id=1,
        conn=aconn,
    )
    assert not should_process, f"Expected rejection, got {action}"
    assert action == "discard:causal_saturation"
    assert meta["parent_id"] == 1
    print(f"✅ Thalamus causal saturation: Rejected (children={meta['children']})")

    # Should pass: different fact_type has 0 children
    should_process2, action2, _ = await gate.filter(
        content="New knowledge about deployment",
        project_id="cortex",
        tenant_id="default",
        fact_type="knowledge",
        parent_decision_id=1,
        conn=aconn,
    )
    assert should_process2, f"Expected pass, got {action2}"
    print(f"✅ Thalamus pass for different fact_type: {action2}")


if __name__ == "__main__":
    test_causal_episode_model()
    asyncio.run(test_trace_episode())
    asyncio.run(test_recall_episode())
    asyncio.run(test_thalamus_causal_saturation())
    print("\n🎯 All Epoch 8 tests passed.")
