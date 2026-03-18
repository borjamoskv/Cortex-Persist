import os

import pytest

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter


@pytest.fixture
def test_db():
    db_path = "test_ledger_checkpointing.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_merkle_checkpoint_creation(test_db):
    store = LedgerStore(test_db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    # 1. Append 15 events
    t = ActionTarget(app="Test")
    r = ActionResult(ok=True, latency_ms=10)

    for i in range(15):
        ev = LedgerEvent.new(
            tool="cli",
            actor="test-actor",
            action=f"action-{i}",
            target=t,
            result=r,
            metadata={"project": "test-proj"},
        )
        writer.append(ev)

    # 2. Checkpoint with batch size 10 (should succeed)
    root_id_1 = verifier.create_checkpoint(batch_size=10)
    assert root_id_1 is not None

    # 3. Check checkpoints table
    with store.tx() as conn:
        cursor = conn.execute(
            "SELECT * FROM ledger_checkpoints WHERE checkpoint_id = ?", (root_id_1,)
        )
        row = cursor.fetchone()
        assert row["event_count"] == 10
        assert row["start_event_id"] is not None
        assert row["end_event_id"] is not None

    # 4. Checkpoint again (remaining 5) with batch size 5
    root_id_2 = verifier.create_checkpoint(batch_size=5)
    assert root_id_2 is not None

    with store.tx() as conn:
        cursor = conn.execute(
            "SELECT * FROM ledger_checkpoints WHERE checkpoint_id = ?", (root_id_2,)
        )
        row = cursor.fetchone()
        assert row["event_count"] == 5

    # 5. Checkpoint again (no more)
    root_id_3 = verifier.create_checkpoint(batch_size=5)
    assert root_id_3 is None
