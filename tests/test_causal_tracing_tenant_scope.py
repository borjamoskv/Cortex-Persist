# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
import pytest

from babylon60.memory.episodic import CausalTracer


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
