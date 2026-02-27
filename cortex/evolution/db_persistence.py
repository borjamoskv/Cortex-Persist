# cortex/evolution/db_persistence.py
"""Database Persistence for Evolution State — Long-Term Memory Consolidation.

Replaces JSON file persistence with CORTEX DB storage, implementing
the hippocampal-cortical complementary learning systems model
(McClelland et al., 1995; O'Reilly & Norman, 2002):

    **Hippocampal buffer** — Rapid one-shot encoding of swarm state
    into the ``evolution_state`` table after each persistence interval.
    Analogous to hippocampal pattern separation (Leutgeb et al., 2007).

    **Cortical consolidation** — Historical snapshots accumulate in the
    DB as a time-series, enabling retrospective analysis and rollback.
    Analogous to neocortical schema assimilation (van Kesteren et al., 2012).

    **Engram retrieval** — ``load_from_db()`` reconstructs the most recent
    swarm state from the latest DB snapshot, functioning as episodic
    recall via hippocampal pattern completion (Marr, 1971).

Schema:
    Table ``evolution_state`` stores JSON-serialised swarm snapshots
    with cycle number and ISO timestamp for temporal indexing.

References:
    Marr, D. (1971). Phil. Trans. R. Soc. Lond. B 262(841), 23–81.
    McClelland, J.L. et al. (1995). Psychological Review 102(3), 419–457.
    O'Reilly, R.C. & Norman, K.A. (2002). Hippocampus 12(6), 821–835.
    van Kesteren, M.T.R. et al. (2012). Trends Neurosci. 35(4), 211–219.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.evolution.agents import SovereignAgent
from cortex.evolution.persistence import (
    SCHEMA_VERSION,
    _agent_to_dict,
    _reconstruct_agents,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path("~/.cortex/cortex.db").expanduser()

# DDL for the evolution_state table (complementary learning systems store)
CREATE_EVOLUTION_STATE = """
CREATE TABLE IF NOT EXISTS evolution_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle       INTEGER NOT NULL,
    state_json  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(cycle)
);
"""


async def ensure_table(db_path: str | Path = _DEFAULT_DB) -> None:
    """Create the evolution_state table if missing.  Idempotent."""
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(CREATE_EVOLUTION_STATE)
        await conn.commit()


async def save_to_db(
    agents: list[SovereignAgent],
    cycle: int,
    db_path: str | Path = _DEFAULT_DB,
) -> None:
    """Persist swarm state to CORTEX DB (hippocampal rapid encoding).

    Uses INSERT OR REPLACE with UNIQUE(cycle) constraint to ensure
    one snapshot per cycle (pattern separation — Leutgeb et al., 2007).
    """
    state = {
        "version": SCHEMA_VERSION,
        "cycle": cycle,
        "agents": [_agent_to_dict(a) for a in agents],
    }
    state_json = json.dumps(state)
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute(CREATE_EVOLUTION_STATE)
        await conn.execute(
            "INSERT OR REPLACE INTO evolution_state (cycle, state_json) VALUES (?, ?)",
            (cycle, state_json),
        )
        await conn.commit()
        logger.debug("💾 Swarm state persisted to DB at cycle %d", cycle)


async def load_from_db(
    db_path: str | Path = _DEFAULT_DB,
) -> tuple[list[SovereignAgent], int] | None:
    """Load the most recent swarm state from CORTEX DB.

    Implements episodic recall via hippocampal pattern completion
    (Marr, 1971): retrieve the latest snapshot and reconstruct
    the full agent hierarchy.

    Returns:
        Tuple of (agents, cycle) or None if no state found.
    """
    db = Path(db_path)
    if not db.exists():
        return None

    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(CREATE_EVOLUTION_STATE)
            async with conn.execute(
                "SELECT state_json, cycle FROM evolution_state ORDER BY cycle DESC LIMIT 1"
            ) as cur:
                row = await cur.fetchone()
                if not row:
                    return None
                state = json.loads(row[0])
                cycle = row[1]
                agents = _reconstruct_agents(state.get("agents", []))
                if agents:
                    logger.info(
                        "♻️ DB engram loaded: cycle %d, %d agents",
                        cycle,
                        len(agents),
                    )
                    return agents, cycle
    except (aiosqlite.Error, json.JSONDecodeError, KeyError) as exc:
        logger.warning("DB engram retrieval failed: %s", exc)

    return None


async def get_evolution_history(
    db_path: str | Path = _DEFAULT_DB,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve historical evolution snapshots (cortical timeline).

    Returns summary data for retrospective analysis — analogous to
    cortical memory replay during offline consolidation
    (McClelland et al., 1995).
    """
    db = Path(db_path)
    if not db.exists():
        return []

    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(CREATE_EVOLUTION_STATE)
            async with conn.execute(
                "SELECT cycle, created_at FROM evolution_state ORDER BY cycle DESC LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                return [{"cycle": r[0], "created_at": r[1]} for r in rows]
    except (aiosqlite.Error, OSError) as exc:
        logger.warning("Evolution history query failed: %s", exc)
        return []
