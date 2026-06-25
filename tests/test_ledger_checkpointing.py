# [C5-REAL] Exergy-Maximized
import os

import pytest

from legacy_research.ledger.models import ActionResult, ActionTarget, LedgerEvent
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.verifier import LedgerVerifier
from legacy_research.ledger.writer import LedgerWriter


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_ledger_checkpointing.db"
    return str(db_path)


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


def test_post_quantum_checkpointing_verification(test_db):
    store = LedgerStore(test_db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    # 1. Append 10 events
    t = ActionTarget(app="Test")
    r = ActionResult(ok=True, latency_ms=10)

    for i in range(10):
        ev = LedgerEvent.new(
            tool="cli",
            actor="test-actor",
            action=f"action-{i}",
            target=t,
            result=r,
            metadata={"project": "test-proj"},
        )
        writer.append(ev)

    # 2. Create checkpoint
    root_id = verifier.create_checkpoint(batch_size=10)
    assert root_id is not None

    # 3. Verify checkpoint signatures
    report = verifier.verify_checkpoint_signatures()
    assert report["valid"] is True
    assert report["checked_checkpoints"] == 1
    assert len(report["violations"]) == 0

    # 4. Verify post-quantum integrated verification
    pq_report = verifier.verify_post_quantum()
    assert pq_report["valid"] is True
    assert pq_report["checked_events"] == 10
    assert pq_report["checked_checkpoints"] == 1
    assert len(pq_report["violations"]) == 0

    # 5. Corrupt the signature in the DB to verify detection
    with store.tx() as conn:
        conn.execute(
            "UPDATE ledger_checkpoints SET mldsa_signature = ?",
            ("00" * 2420,),  # dummy invalid signature of correct length
        )

    # 6. Verify signatures should now fail
    corrupted_report = verifier.verify_checkpoint_signatures()
    assert corrupted_report["valid"] is False
    assert corrupted_report["checked_checkpoints"] == 1
    assert any("Invalid ML-DSA signature" in v for v in corrupted_report["violations"])

    # 7. Corrupt the root hash to verify detection
    with store.tx() as conn:
        conn.execute(
            "UPDATE ledger_checkpoints SET root_hash = ?",
            ("corrupted_hash",),
        )

    corrupted_report_2 = verifier.verify_checkpoint_signatures()
    assert corrupted_report_2["valid"] is False
    assert corrupted_report_2["checked_checkpoints"] == 1
