# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)
"""Tests for the Composition Leakage Shield (v7.0) in PrivacyMixin."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from cortex.engine import CortexEngine
from cortex.extensions.security.signatures import get_default_signer


@pytest.fixture
async def engine(tmp_path: Path, monkeypatch):
    """Create a CortexEngine with a temp database, close after test."""
    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    monkeypatch.setenv("CORTEX_NO_TAINT_ENFORCE", "1")  # Bypass taint token trigger

    db = str(tmp_path / "test_privacy_composition.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    # Ensure causal_edges exists
    from cortex.engine.flow.causality import AsyncCausalGraph
    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
        await cg.ensure_table()

    yield e
    await e.close()


@pytest.mark.asyncio
async def test_composition_leakage_eth_address_and_salt(engine: CortexEngine):
    """Storing an eth_address and then a salt in the same project should trigger composition leakage shield."""
    # 1. Store Fact A: eth_address (innocuous)
    fact_id_a = await engine.store(
        project="prod-deploy",
        content="Contract will be deployed at address: 0x3065da4ea92c90c74f56f112423377756f112423",
        source="agent:deployer",
    )

    # Fetch Fact A metadata and verify it is not flagged for composition leakage initially
    async with engine.session() as conn:
        async with conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id_a,)) as cursor:
            row = await cursor.fetchone()
            import json
            meta_a = json.loads(row[0]) if row else {}
            assert "composition_leakage" not in meta_a

    # 2. Store Fact B: salt (innocuous by itself, but correlates with address)
    fact_id_b = await engine.store(
        project="prod-deploy",
        content="Salt for the proxy deploy is salt: 0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        source="agent:deployer",
    )

    # 3. Verify Fact B has composition leakage metadata
    async with engine.session() as conn:
        async with conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id_b,)) as cursor:
            row = await cursor.fetchone()
            meta_b = json.loads(row[0]) if row else {}
            assert meta_b.get("composition_leakage") is True
            assert "contract_deploy_composition" in meta_b.get("composition_categories", [])
            assert fact_id_a in meta_b.get("correlated_fact_ids", [])

        # 4. Verify Fact A was retroactively updated in the DB
        async with conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id_a,)) as cursor:
            row = await cursor.fetchone()
            updated_meta_a = json.loads(row[0]) if row else {}
            assert updated_meta_a.get("composition_leakage") is True
            assert updated_meta_a.get("composition_category") == "contract_deploy_composition"


@pytest.mark.asyncio
async def test_composition_leakage_different_projects(engine: CortexEngine):
    """Correlation should not trigger if facts belong to different projects/tenants."""
    fact_id_a = await engine.store(
        project="project-alpha",
        content="Contract will be deployed at address: 0x3065da4ea92c90c74f56f112423377756f112423",
        source="agent:deployer",
    )

    fact_id_b = await engine.store(
        project="project-beta",
        content="Salt for the proxy deploy is salt: 0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        source="agent:deployer",
    )

    async with engine.session() as conn:
        async with conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id_b,)) as cursor:
            row = await cursor.fetchone()
            import json
            meta_b = json.loads(row[0]) if row else {}
            assert "composition_leakage" not in meta_b
