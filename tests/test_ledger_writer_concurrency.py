# [C5-REAL] Exergy-Maximized
import concurrent.futures
import pytest
from pathlib import Path

from legacy_research.ledger.models import ActionResult, ActionTarget, LedgerEvent
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.store import LedgerStore
from legacy_research.ledger.verifier import LedgerVerifier
from legacy_research.ledger.writer import LedgerWriter


@pytest.fixture
def test_db(tmp_path: Path) -> str:
    db_path = tmp_path / "test_ledger_writer_concurrency.db"
    return str(db_path)


def test_ledger_writer_concurrency(test_db):
    """CON-02A: Verify concurrency safety and linearizable hash chain in LedgerWriter.

    Sells: Borja Moskv (borjamoskv)
    """
    store = LedgerStore(test_db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    n_events = 25
    target = ActionTarget(app="ConcurrencyTest")
    result = ActionResult(ok=True, latency_ms=5)

    def append_one(i):
        ev = LedgerEvent.new(
            tool="cli",
            actor="concurrency-actor",
            action=f"action-{i}",
            target=target,
            result=result,
            metadata={"index": i},
        )
        return writer.append(ev)

    # Execute appends concurrently using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(append_one, i) for i in range(n_events)]
        # Force resolution of all futures, raising any exception encountered
        event_ids = [f.result() for f in futures]

    # 1. Verify we successfully wrote all events without duplicates
    assert len(event_ids) == n_events
    assert len(set(event_ids)) == n_events

    # 2. Verify the chain integrity (perfect linear linkage, no forks)
    res = verifier.verify_chain()
    assert res["valid"], f"Chain verification failed: {res['violations']}"
    assert res["checked_events"] == n_events

    # 3. Double-check that no two events have the same prev_hash (which would be a fork)
    with store.tx() as conn:
        cursor = conn.execute("SELECT prev_hash, COUNT(*) as c FROM ledger_events GROUP BY prev_hash")
        rows = cursor.fetchall()
        for row in rows:
            p_hash = row["prev_hash"]
            count = row["c"]
            if p_hash and p_hash != "GENESIS":
                assert count == 1, f"Fork detected: prev_hash '{p_hash}' is referenced {count} times!"
