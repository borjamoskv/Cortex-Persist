"""Tests for stats() tenant isolation in CORTEX Engine."""

import pytest

from cortex.engine import CortexEngine
from cortex.extensions.security.tenant import tenant_id_var


@pytest.fixture
async def engine(tmp_path):
    db_path = str(tmp_path / "test_stats.db")
    e = CortexEngine(db_path=db_path, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


@pytest.mark.asyncio
async def test_engine_stats_isolation(engine):
    """Verify that QueryMixin.stats() filters by tenant_id correctly."""

    # Alice: 2 facts in 'alpha', 1 in 'beta'
    token_alice = tenant_id_var.set("tenant-alice")
    await engine.store(content="Alice's secret strategy for Alpha", project="alpha", source="api")
    await engine.store(content="Alice's second finding for Alpha", project="alpha", source="api")
    await engine.store(content="Alice's secret strategy for Beta", project="beta", source="api")
    tenant_id_var.reset(token_alice)

    # Bob: 1 fact in 'alpha'
    token_bob = tenant_id_var.set("tenant-bob")
    await engine.store(content="Bob's secret strategy for Alpha", project="alpha", source="api")
    tenant_id_var.reset(token_bob)

    # Check Alice stats
    alice_stats = await engine.stats(tenant_id="tenant-alice")
    assert alice_stats["total_facts"] == 3
    assert alice_stats["active_facts"] == 3
    assert alice_stats["project_count"] == 2
    assert "alpha" in alice_stats["projects"]
    assert "beta" in alice_stats["projects"]

    # Check Bob stats
    bob_stats = await engine.stats(tenant_id="tenant-bob")
    assert bob_stats["total_facts"] == 1
    assert bob_stats["active_facts"] == 1
    assert bob_stats["project_count"] == 1
    assert "alpha" in bob_stats["projects"]
    assert "beta" not in bob_stats["projects"]

    # Check non-existent tenant
    null_stats = await engine.stats(tenant_id="tenant-void")
    assert null_stats["total_facts"] == 0
    assert null_stats["project_count"] == 0
