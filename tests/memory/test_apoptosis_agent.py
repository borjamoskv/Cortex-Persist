# [C5-REAL] Exergy-Maximized
"""
Unit tests for the ApoptosisAgent (Poda de Datos y Compresión Shannon).
"""

import os
import sqlite3
import pytest
from unittest.mock import AsyncMock

from cortex.memory.apoptosis import ApoptosisAgent
from cortex.database.schema import CREATE_FACTS
from cortex.database.core import connect_async_ctx, causal_write


@pytest.fixture
async def temp_db(tmp_path):
    db_file = str(tmp_path / "test_apoptosis.db")
    async with connect_async_ctx(db_file) as conn:
        with causal_write(conn):
            await conn.execute(CREATE_FACTS)
            await conn.commit()
    return db_file


@pytest.mark.asyncio
async def test_apoptosis_agent_shannon_calculation():
    # Verify math is correct for Shannon calculation
    agent = ApoptosisAgent(db_path="mock.db")
    
    # Repetitive slop has low entropy
    low_entropy = agent.calculate_shannon_entropy("aaaaa")
    # Structured string has higher entropy
    high_entropy = agent.calculate_shannon_entropy("abcde")
    
    assert low_entropy < high_entropy
    assert agent.calculate_shannon_entropy("") == 0.0


@pytest.mark.asyncio
async def test_apoptosis_agent_prunes_low_energy_and_slop(temp_db):
    # Setup agent with free-tier atp threshold = 0.4
    agent = ApoptosisAgent(db_path=temp_db, atp_free_threshold=0.4, max_free_facts=10)

    async with connect_async_ctx(temp_db) as conn:
        with causal_write(conn):
            # 1. High exergy useful fact (should keep)
            await conn.execute(
                "INSERT INTO facts (project, content, tenant_id, exergy_score, is_tombstoned) VALUES (?, ?, ?, ?, 0)",
                ("proj", "This is a very high quality structured fact for execution.", "free-tenant", 1.0)
            )
            # 2. Borderline energy fact (0.5), but it has conversational noise (under 15 chars) -> decayed to 0.25 (should prune)
            await conn.execute(
                "INSERT INTO facts (project, content, tenant_id, exergy_score, is_tombstoned) VALUES (?, ?, ?, ?, 0)",
                ("proj", "thanks!", "free-tenant", 0.5)
            )
            # 3. Already low energy fact (0.3) -> should prune
            await conn.execute(
                "INSERT INTO facts (project, content, tenant_id, exergy_score, is_tombstoned) VALUES (?, ?, ?, ?, 0)",
                ("proj", "Random fact content with low energy.", "free-tenant", 0.3)
            )
            await conn.commit()

    stats = await agent.run_apoptosis_cycle("free-tenant")
    assert stats["scanned"] == 3
    assert stats["tombstoned"] == 2

    # Verify rows in DB
    async with connect_async_ctx(temp_db) as conn:
        async with conn.execute("SELECT content, is_tombstoned FROM facts WHERE tenant_id = 'free-tenant'") as cursor:
            rows = await cursor.fetchall()
            results = {r[0]: r[1] for r in rows}
            assert results["This is a very high quality structured fact for execution."] == 0
            assert results["thanks!"] == 1
            assert results["Random fact content with low energy."] == 1


@pytest.mark.asyncio
async def test_apoptosis_agent_enforces_capacity_limit(temp_db):
    # Setup agent with max 3 free facts
    agent = ApoptosisAgent(db_path=temp_db, atp_free_threshold=0.1, max_free_facts=3)

    async with connect_async_ctx(temp_db) as conn:
        with causal_write(conn):
            # Insert 5 facts with different exergy scores
            for i in range(5):
                await conn.execute(
                    "INSERT INTO facts (project, content, tenant_id, exergy_score, is_tombstoned) VALUES (?, ?, ?, ?, 0)",
                    ("proj", f"Fact number {i} content text", "free-tenant", float(i + 1) / 10.0)
                )
            await conn.commit()

    stats = await agent.run_apoptosis_cycle("free-tenant")
    assert stats["scanned"] == 5
    # Since max is 3, 2 facts should be tombstoned
    assert stats["tombstoned"] == 2

    # Verify that the two facts with the lowest exergy scores (Fact 0: 0.1, Fact 1: 0.2) were tombstoned
    async with connect_async_ctx(temp_db) as conn:
        async with conn.execute("SELECT content, is_tombstoned FROM facts WHERE tenant_id = 'free-tenant' ORDER BY exergy_score ASC") as cursor:
            rows = await cursor.fetchall()
            assert rows[0][1] == 1  # lowest (Fact 0) -> tombstoned
            assert rows[1][1] == 1  # second lowest (Fact 1) -> tombstoned
            assert rows[2][1] == 0  # third lowest -> kept
