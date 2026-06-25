
import pytest
import aiosqlite

from cortex.engine.causality import AsyncCausalGraph
from cortex.migrations.mig_temporal_kg import _migration_027_temporal_kg




@pytest.mark.asyncio
async def test_temporal_causal_chain():
    async with aiosqlite.connect(":memory:") as db:
        # Create schema
        await db.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                decay_half_life REAL DEFAULT 30.0,
                tenant_id TEXT DEFAULT 'default'
            )
        """)

        await db.execute("""
            CREATE TABLE causal_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER NOT NULL,
                parent_id INTEGER,
                signal_id INTEGER,
                edge_type TEXT NOT NULL DEFAULT 'triggered_by',
                confidence REAL DEFAULT 1.0,
                agent_id TEXT,
                project TEXT,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (fact_id) REFERENCES facts(id)
            )
        """)
        await db.commit()

        # Insert some facts
        await db.execute("INSERT INTO facts (id, content) VALUES (1, 'Fact A')")
        await db.execute("INSERT INTO facts (id, content) VALUES (2, 'Fact B')")
        await db.execute("INSERT INTO facts (id, content) VALUES (3, 'Fact C')")
        await db.commit()

        graph = AsyncCausalGraph(db)

        # A -> B -> C
        await graph.record_edge(fact_id=2, parent_id=1, confidence=0.9, agent_id="agent_1")
        await graph.record_edge(fact_id=3, parent_id=2, confidence=0.8, agent_id="agent_2")
        await db.commit()

        chain = await graph.temporal_causal_chain(target_fact_id=3, hours_lookback=24)

        assert len(chain) == 2
        # First degree ancestor
        assert chain[0]["ancestor_id"] == 2
        assert chain[0]["child_id"] == 3
        assert chain[0]["confidence"] == 0.8
        assert chain[0]["depth"] == 1

        # Second degree ancestor
        assert chain[1]["ancestor_id"] == 1
        assert chain[1]["child_id"] == 2
        assert chain[1]["confidence"] == pytest.approx(0.72)  # 0.9 * 0.8
        assert chain[1]["depth"] == 2
