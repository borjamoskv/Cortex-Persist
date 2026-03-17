from __future__ import annotations


def test_ledger_append_survives_without_embeddings(tmp_path):
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore
    from cortex.ledger.writer import LedgerWriter
    from cortex.mac_maestro.events import build_mac_maestro_event

    db = tmp_path / "ledger.db"
    store = LedgerStore(db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)

    event = build_mac_maestro_event(
        action="click",
        app="com.apple.TextEdit",
        role="AXButton",
        title="Save",
        identifier=None,
        ok=True,
        latency_ms=42,
    )
    event_id = writer.append(event)

    assert isinstance(event_id, str)
    with store.tx() as conn:
        row = conn.execute(
            "SELECT semantic_status FROM ledger_events WHERE event_id=?",
            (event_id,),
        ).fetchone()

    assert row is not None
    assert row["semantic_status"] == "pending"
