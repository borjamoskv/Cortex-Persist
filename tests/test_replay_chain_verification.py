# [C5-REAL] Exergy-Maximized
"""
Verification tests for Cryptographic Trajectory Verification (Epoch 15).
"""
import pytest
import hashlib

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.forensic.replay import ReplayEngine


class MockLedgerConnection:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, params=None):
        # Must return an awaitable or context manager wrapper
        return AioMockCursor(self.rows)

class AioMockCursor:
    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return MockCursor(self.rows)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockCursor:
    def __init__(self, rows):
        self.rows = rows
        self.idx = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.idx >= len(self.rows):
            raise StopAsyncIteration
        row = self.rows[self.idx]
        self.idx += 1
        return row


@pytest.mark.asyncio
async def test_replay_engine_verification():
    """Verify that ReplayEngine extracts and parses trajectories correctly."""
    # timestamp, action, resource, status, prev_hash, signature
    rows = [
        ("audit_1", "2026-06-28T19:00:00Z", "task:start", "resource_1", "success", "GENESIS", "sig_1"),
        ("audit_2", "2026-06-28T19:01:00Z", "task:step", "resource_2", "success", "hash_1", "sig_2"),
    ]
    
    conn = MockLedgerConnection(rows)
    # We mock EnterpriseAuditLedger to bypass key loading
    class MockLedger(EnterpriseAuditLedger):
        def __init__(self, connection):
            self._conn = connection
            self._ready = True

        async def ensure_table(self):
            pass

    ledger = MockLedger(conn)
    engine = ReplayEngine(ledger)
    
    trajectory = await engine.extract_trajectory(tenant_id="default", actor_id="agent_1")
    
    assert len(trajectory) == 2
    assert trajectory[0]["audit_id"] == "audit_1"
    assert trajectory[0]["prev_hash"] == "GENESIS"
    assert trajectory[1]["audit_id"] == "audit_2"
    assert trajectory[1]["prev_hash"] == "hash_1"
