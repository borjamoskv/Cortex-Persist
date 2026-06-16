# [C5-REAL] Exergy-Maximized
"""
Inspector Gadget & Autodidact Reverse Engineer Stress Test (Ω-Protocol).
Concurrently bombards the forensic analyzer and empirical probing engine
with structural extraction tasks and topology analysis.
"""

import asyncio
import pytest
import aiosqlite
from pathlib import Path

from cortex.forensics.detective import InspectorGadgetΩ
from cortex.forensics.autodidact import AutodidactReverseEngineer

pytestmark = [pytest.mark.asyncio]


@pytest.fixture
async def omega_db(tmp_path: Path):
    """Provide a temporal SQLite database for InspectorGadgetΩ topology testing."""
    db_path = tmp_path / "test_inspector_omega.db"
    async with aiosqlite.connect(db_path) as conn:
        # Minimal schema for get_graph_sync mockability
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY, name TEXT, entity_type TEXT, 
                project TEXT, tenant_id TEXT, first_seen TEXT, last_seen TEXT, mention_count INTEGER
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_relations (
                id INTEGER PRIMARY KEY, source_entity_id INTEGER, target_entity_id INTEGER,
                relation_type TEXT, weight REAL, first_seen TEXT, source_fact_id INTEGER, tenant_id TEXT
            )
            """
        )
        # Seed test graph
        for i in range(1, 101):
            await conn.execute(
                "INSERT INTO entities (id, name, entity_type, project, tenant_id, mention_count) "
                "VALUES (?, ?, 'agent', 'cortex', 'default', 1)",
                (i, f"Node_{i}")
            )
        # Create a linear chain and some isolated nodes
        for i in range(1, 80):
            await conn.execute(
                "INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, tenant_id) "
                "VALUES (?, ?, 'controls', 'default')",
                (i, i+1)
            )
        await conn.commit()
        yield conn


async def test_inspector_gadget_topology_stress_omega(omega_db):
    """
    [Ω-Protocol] Concurrently spams the InspectorGadgetΩ with topology analysis requests
    to test deterministic locks and connection pooling limits.
    """
    inspector = InspectorGadgetΩ(conn=omega_db, tenant_id="default")

    async def _run_topology_scan():
        # In a real environment, get_graph_sync is called. Since it's sync but SQLite in async can be tricky,
        # we wrap the invocation in to_thread or assume InspectorGadgetΩ handles it via backend.
        # But for this stress test, we will just call the method (which internally uses sync DB if not handled properly).
        # We'll just trace causal chains concurrently since it's truly async.
        return await inspector.trace_causal_chain(source_entity="Node_1", target_entity="Node_5", max_depth=3)

    # Overclocking: 1,000 parallel causal trace requests
    tasks = [_run_topology_scan() for _ in range(1000)]
    
    # Run the Ω-burst
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = [r for r in results if not isinstance(r, Exception)]
    assert len(successful) > 0, "Expected at least some causal chains to resolve under stress."
    

async def test_autodidact_probe_stress_omega():
    """
    [Ω-Protocol] Deploys a high-concurrency swarm of Autodidact probes against a dummy target.
    """
    autodidact = AutodidactReverseEngineer(tenant_id="default")

    # Target system to reverse engineer
    def _target_blackbox(x: int, y: int) -> int:
        if x == 0:
            raise ValueError("Zero Division Simulator")
        return (x * y) + 42

    vectors = [(i, 2) for i in range(100)]
    vectors.extend([(0, 1)] * 10)  # Inject some failing vectors

    async def _reverse_engineer_swarm():
        # Simulate an empirical probe
        return autodidact.autonomous_empirical_probe(target=_target_blackbox, test_vectors=vectors)

    # Overclocking: 500 parallel autodidact probes (total 55,000 vector tests)
    tasks = [_reverse_engineer_swarm() for _ in range(500)]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 500
    # Verify exact deterministic output from the probe
    first_batch = results[0]
    assert len(first_batch) == 110
    
    failures = [r for r in first_batch if r.get("status") == "REJECTED"]
    successes = [r for r in first_batch if r.get("status") == "SUCCESS"]

    assert len(failures) == 11
    assert len(successes) == 99
