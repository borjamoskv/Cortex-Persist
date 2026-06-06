# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import aiosqlite
import pytest

from cortex.memory.episodic import CausalTracer


async def _setup_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            parent_decision_id INTEGER
        );
        """
    )
    await conn.commit()


@pytest.mark.asyncio
async def test_trace_episode_is_tenant_scoped() -> None:
    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    await conn.executemany(
        "INSERT INTO facts (id, tenant_id, project, content, fact_type, parent_decision_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "alpha", "alpha-project", "alpha root", "decision", None),
            (2, "alpha", "alpha-project", "alpha child", "knowledge", 1),
            (3, "beta", "beta-project", "beta intruder", "knowledge", 1),
        ],
    )
    await conn.commit()

    tracer = CausalTracer(conn)
    episode = await tracer.trace_episode(1, tenant_id="alpha")

    assert [node["id"] for node in episode.fact_chain] == [1, 2]
    assert episode.project == "alpha-project"

    await conn.close()
