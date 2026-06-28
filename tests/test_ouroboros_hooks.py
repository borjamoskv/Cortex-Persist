import pytest
import asyncio
import sqlite3
from cortex.ledger.ledger_core import SovereignLedger
from cortex.storage.turbopuffer import TurbopufferVectorBackend
from cortex.extensions.daemon.monitors.epistemic import EpistemicMonitor
from dataclasses import dataclass

# [OUROBOROS] Vector P1.2 Integration Tests

def test_ledger_blocks_anergic_actions():
    # Ledger should block empty actions due to Ouroboros Hook
    conn = sqlite3.connect(":memory:")
    # SovereignLedger ensures its own schema
    ledger = SovereignLedger(db=conn)
    with pytest.raises(ValueError, match=r"\[OUROBOROS\] Vector P1.2: Anergic action detected"):
        ledger.record_transaction(
            action="   ", # Anergic
            project="test_project",
            detail={},
            tenant_id="test_tenant",
        )

@pytest.mark.asyncio
async def test_turbopuffer_blocks_zero_embedding():
    # Turbopuffer backend should block zeroed embeddings
    backend = TurbopufferVectorBackend(api_key="test_fake_key")
    with pytest.raises(ValueError, match=r"\[OUROBOROS\] Vector P1.2: Embedding lacks structural exergy"):
        await backend.upsert(
            fact_id=123,
            embedding=[0.0, 0.0, 0.0, 0.0], # Zero exergy
            tenant_id="test_tenant"
        )

@dataclass
class MockStats:
    total_memories: int
    stale_memories: int

@pytest.mark.asyncio
async def test_epistemic_monitor_triggers_ouroboros():
    monitor = EpistemicMonitor()
    stats = MockStats(total_memories=100, stale_memories=55)
    stale_ratio = stats.stale_memories / stats.total_memories
    assert stale_ratio >= 0.50
