"""
Compliance Siege Test — Live Red Team Assault on Ledger & Vault (Inmunología Evolutiva)

Validates that the system survives mass concurrent, malicious mutations.
"""

import asyncio

import pytest

from cortex.crypto.vault import Vault
from cortex.database.pool import CortexConnectionPool
from cortex.engine.legion_vectors import COMPLIANCE_SIEGE_SWARM
from cortex.engine_async import AsyncCortexEngine
from cortex.migrations.core import run_migrations_async


@pytest.fixture
async def siege_engine(tmp_path):
    db_path = tmp_path / "siege.db"
    pool = CortexConnectionPool(str(db_path), min_connections=2, max_connections=4, read_only=False)
    await pool.initialize()
    async with pool.acquire() as conn:
        await run_migrations_async(conn)

    engine = AsyncCortexEngine(pool, str(db_path))

    # We force a vault key for testing
    engine.vault = Vault(Vault.generate_key().encode("utf-8"))

    # Setup some initial facts
    await engine.store("test_project", "Genesis fact string", fact_type="knowledge")
    await engine.store("test_project", "Fact number two", fact_type="decision")

    if engine._ledger:
        await engine._ledger.create_checkpoint_async()

    yield engine
    await pool.close()


@pytest.mark.asyncio
async def test_compliance_siege_survives(siege_engine: AsyncCortexEngine):
    """
    Run COMPLIANCE_SIEGE_SWARM against the engine.
    If the ledger is truly immutable and BFT, NO attack should generate a 'finding'.
    """
    all_findings = []

    # Launch attacks in parallel
    tasks = []
    for vector in COMPLIANCE_SIEGE_SWARM:
        tasks.append(vector.attack(siege_engine, {}))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, list):
            all_findings.extend(r)

    # Verify the internal state logic
    report = await siege_engine.verify_ledger()

    # If the ledger was poisoned, report["valid"] will be False.
    # The attacks collect 'findings' if they thought they succeeded.

    if all_findings:
        pytest.fail("RED TEAM BREACHED COMPLIANCE:\n" + "\n".join(all_findings))

    assert report["valid"] is True, f"Ledger integrity broken: {report['violations']}"
