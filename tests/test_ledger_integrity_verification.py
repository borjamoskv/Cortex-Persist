import os

import pytest

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter


@pytest.fixture
def test_db():
    db_path = "test_ledger_integrity.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_ledger_integrity_chain(test_db):
    store = LedgerStore(test_db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    # 1. Append valid events
    t = ActionTarget(app="Test")
    r = ActionResult(ok=True, latency_ms=10)
    
    for i in range(5):
        ev = LedgerEvent.new(
            tool="cli", actor="test-actor", action=f"action-{i}", 
            target=t, result=r, metadata={"project": "test-proj"}
        )
        writer.append(ev)

    # 2. Verify chain is valid
    res = verifier.verify_chain()
    assert res["valid"] == True
    assert res["checked_events"] == 5

    # 3. Corrupt hash
    with store.tx() as conn:
        # Find the 3rd event by rowid
        cursor = conn.execute("SELECT event_id FROM ledger_events LIMIT 1 OFFSET 2")
        ev_id = cursor.fetchone()["event_id"]
        conn.execute("UPDATE ledger_events SET hash = 'BADHASH' WHERE event_id = ?", (ev_id,))
    
    # 4. Verify detects COMPROMISED
    res = verifier.verify_chain()
    assert res["valid"] == False
    assert any("Hash mismatch" in v or "Chain break" in v for v in res["violations"])

def test_ledger_chain_break(test_db):
    store = LedgerStore(test_db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    # 2 events
    t = ActionTarget(app="Test")
    r = ActionResult(ok=True, latency_ms=10)
    for i in range(2):
        ev = LedgerEvent.new(tool="cli", actor="test", action=f"a{i}", target=t, result=r)
        writer.append(ev)
    
    # Break the chain by altering prev_hash of the second one
    with store.tx() as conn:
        cursor = conn.execute("SELECT event_id FROM ledger_events LIMIT 1 OFFSET 1")
        ev_id = cursor.fetchone()["event_id"]
        conn.execute("UPDATE ledger_events SET prev_hash = 'WRONG_PREV' WHERE event_id = ?", (ev_id,))
    
    res = verifier.verify_chain()
    assert res["valid"] == False
    assert any("Chain break" in v for v in res["violations"])
