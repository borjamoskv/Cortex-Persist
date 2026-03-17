"""Tests for Bounded Demolition (Axiom Ω₄)."""

from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.engine.causality import EDGE_DERIVED_FROM, AsyncCausalGraph


@pytest.fixture
async def engine(tmp_path: Path, monkeypatch):
    # Mock Frontier-compliant configuration to satisfy Rule 1.3
    monkeypatch.setenv("CORTEX_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("CORTEX_LLM_MODEL", "gemini-3.1-pro-preview")
    from cortex import config
    config.reload()

    db = str(tmp_path / "test_purge.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    
    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
    
    yield e
    await e.close()

class TestPurgeBounded:
    async def test_purge_simple_fact_allowed(self, engine):
        fact_id = await engine.store(
            project="test",
            content="Simple fact with no dependencies.",
            fact_type="knowledge"
        )
        
        result = await engine.purge(fact_id)
        assert result is True
        
        # Verify it's gone
        async with engine.session() as conn:
            async with conn.execute("SELECT id FROM facts WHERE id = ?", (fact_id,)) as cursor:
                assert await cursor.fetchone() is None

    async def test_purge_rule_with_dependencies_denied(self, engine):
        # 1. Create a rule fact
        rule_id = await engine.store(
            project="test",
            content="IF x THEN y",
            fact_type="rule"
        )
        
        # 2. Create 5 dependent facts to reach criticality > 0.8
        # Heuristic: 0.5 (rule) + min(0.4, 5 * 0.1) = 0.9
        for i in range(5):
            child_id = await engine.store(
                project="test",
                content=f"Dependent fact {i}",
                parent_decision_id=rule_id
            )
            # Ensure causal edge is created (if store doesn't do it automatically for these types)
            async with engine.session() as conn:
                await conn.execute(
                    "INSERT INTO causal_edges (fact_id, parent_id, edge_type) VALUES (?, ?, ?)",
                    (child_id, rule_id, EDGE_DERIVED_FROM)
                )
                await conn.commit()

        # 3. Purge should fail
        with pytest.raises(RuntimeError, match="Bounded Demolition Denied"):
            await engine.purge(rule_id)

        # 4. Success with force
        result = await engine.purge(rule_id, force=True)
        assert result is True
        
        # 5. Verify edges are also gone
        async with engine.session() as conn:
            async with conn.execute(
                "SELECT count(*) FROM causal_edges WHERE fact_id = ? OR parent_id = ?",
                (rule_id, rule_id)
            ) as cursor:
                row = await cursor.fetchone()
                assert row[0] == 0

    async def test_purge_knowledge_with_dependencies_allowed_but_quarantined_logic(self, engine):
        # Knowledge facts max out at 0.4 criticality in current heuristic,
        # so they are allowed. Let's verify they ARE deleted.
        fact_id = await engine.store(
            project="test",
            content="Knowledge fact with dependencies.",
            fact_type="knowledge"
        )
        
        for i in range(5):
            child_id = await engine.store(
                project="test",
                content=f"Dependent {i}",
                parent_decision_id=fact_id
            )
            async with engine.session() as conn:
                await conn.execute(
                    "INSERT INTO causal_edges (fact_id, parent_id, edge_type) VALUES (?, ?, ?)",
                    (child_id, fact_id, EDGE_DERIVED_FROM)
                )
                await conn.commit()

        # Should be allowed (crit=0.4 <= 0.8)
        result = await engine.purge(fact_id)
        assert result is True
        
        async with engine.session() as conn:
            async with conn.execute("SELECT id FROM facts WHERE id = ?", (fact_id,)) as cursor:
                assert await cursor.fetchone() is None
