"""End-to-end integration test validating the Persistence & Consensus Ledger chain.

Proves GHOST-W5-01: task -> CORTEX persist -> Postgres/SQLite -> hash chain verify.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from cortex.consensus.ledger import ImmutableLedger
from cortex.engine import CortexEngine


@pytest.fixture
async def engine():
    """Create a temporary CORTEX engine for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    eng = CortexEngine(db_path=db_path, auto_embed=False)
    await eng.init_db()
    yield eng
    await eng.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_end_to_end_store_and_verify_ledger(engine: CortexEngine) -> None:
    """Verify that storing a fact correctly appends to the verified hash chain."""

    # 1. Start with an Engine and store a couple of facts.
    tenant_id = "test_tenant"
    project = "test_e2e_ledger"

    fact_id_1 = await engine.store(
        project=project,
        content="[E2E] First test fact for integration testing.",
        tenant_id=tenant_id,
        fact_type="knowledge",
        source="test_full_chain",
    )

    fact_id_2 = await engine.store(
        project=project,
        content="[E2E] Second test fact for integration testing.",
        tenant_id=tenant_id,
        fact_type="knowledge",
        source="test_full_chain",
    )

    assert fact_id_1 is not None
    assert fact_id_2 is not None
    assert fact_id_1 != fact_id_2

    # 2. Check that the ledger validates the integrity of the chain.
    conn = await engine.get_conn()
    ledger = ImmutableLedger(conn)

    # Generate a Merkle checkpoint (force batch size to 1 for testing)
    import unittest.mock

    from cortex import config

    with unittest.mock.patch.object(config, "CHECKPOINT_MAX", 1):
        await ledger.create_checkpoint_async()

    results = await ledger.verify_integrity_async()

    assert results["valid"] is True, f"Chain integrity compromised: {results['violations']}"
    assert results["tx_checked"] >= 2
    assert results["roots_checked"] >= 1
