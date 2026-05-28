import dataclasses

from cortex.ledger.models import LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore


class LedgerWriter:
    def __init__(self, store: LedgerStore, queue: EnrichmentQueue) -> None:
        self.store = store
        self.queue = queue

    def append(self, event: LedgerEvent) -> str:
        with self.store.tx() as conn:
            # 1. Get last hash
            cursor = conn.execute("SELECT hash FROM ledger_events ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row["hash"] if row else "GENESIS"

            # 2. Compute current hash
            new_hash = event.compute_hash(prev_hash)
            event = dataclasses.replace(event, prev_hash=prev_hash, hash=new_hash)

            conn.execute(
                """
                INSERT INTO ledger_events (
                    event_id, ts, tool, actor, action, payload_json,
                    prev_hash, hash,
                    semantic_status, semantic_error, correlation_id, trace_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    event.event_id,
                    event.ts,
                    event.tool,
                    event.actor,
                    event.action,
                    event.to_json(),
                    event.prev_hash,
                    event.hash,
                    event.semantic_status,
                    event.correlation_id,
                    event.trace_id,
                ),
            )

        self.queue.enqueue(event.event_id)
        return event.event_id
