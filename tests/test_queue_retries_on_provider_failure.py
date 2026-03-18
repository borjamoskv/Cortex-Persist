from __future__ import annotations


def test_queue_retries_on_provider_failure(tmp_path):
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore

    db = tmp_path / "ledger.db"
    store = LedgerStore(db)
    queue = EnrichmentQueue(store)

    with store.tx() as conn:
        conn.execute(
            """
            INSERT INTO ledger_events (event_id, ts, tool, actor, action, payload_json, semantic_status)
            VALUES ('e1', '2026-03-18T00:00:00Z', 'mac_maestro', 'agent', 'click', '{}', 'pending')
            """
        )

    job_id = queue.enqueue("e1")
    claimed = queue.claim_one()
    assert claimed is not None

    queue.mark_failed(job_id, "e1", "provider down", attempts=0)

    with store.tx() as conn:
        row = conn.execute(
            """
            SELECT status, attempts, last_error
            FROM enrichment_jobs
            WHERE job_id=?
            """,
            (job_id,),
        ).fetchone()

    assert row is not None
    assert row["status"] == "retry"
    assert row["attempts"] == 1
    assert "provider down" in row["last_error"]
