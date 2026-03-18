from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cortex.ledger.store import LedgerStore


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EnrichmentQueue:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    def enqueue(self, event_id: str) -> str:
        job_id = str(uuid.uuid4())
        with self.store.tx() as conn:
            conn.execute(
                """
                INSERT INTO ledger_enrichment_jobs (job_id, event_id, status, attempts, next_attempt_ts)
                VALUES (?, ?, 'queued', 0, ?)
                """,
                (job_id, event_id, utc_now_iso()),
            )
        return job_id

    def claim_one(self) -> Optional[dict[str, Any]]:
        """Atomically claim a job for processing.
        
        Uses SQLite's RETURNING clause (3.35.0+) to ensure only one worker
        claims each job, even under high concurrency.
        """
        with self.store.tx() as conn:
            # We must use a subquery to find the candidate ID, then update it.
            # RETURNING gives us the row values after the update.
            row = conn.execute(
                """
                UPDATE ledger_enrichment_jobs
                SET status='processing', updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE job_id = (
                    SELECT job_id
                    FROM ledger_enrichment_jobs
                    WHERE status IN ('queued', 'retry')
                      AND (next_attempt_ts IS NULL OR next_attempt_ts <= ?)
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING job_id, event_id, attempts
                """,
                (utc_now_iso(),),
            ).fetchone()

            if row is None:
                return None

            conn.execute(
                "UPDATE ledger_events SET semantic_status='processing' WHERE event_id=?",
                (row["event_id"],),
            )
            return dict(row)

    def mark_done(self, job_id: str, event_id: str) -> None:
        with self.store.tx() as conn:
            conn.execute(
                """
                UPDATE ledger_enrichment_jobs
                SET status='done', updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE job_id=?
                """,
                (job_id,),
            )
            conn.execute(
                """
                UPDATE ledger_events
                SET semantic_status='indexed', semantic_error=NULL
                WHERE event_id=?
                """,
                (event_id,),
            )

    def mark_failed(self, job_id: str, event_id: str, error: str, attempts: int) -> None:
        delay_minutes = min(60, 2 ** min(attempts, 5))
        next_attempt = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).isoformat()
        terminal = attempts >= 8

        with self.store.tx() as conn:
            conn.execute(
                """
                UPDATE ledger_enrichment_jobs
                SET status=?, attempts=?, next_attempt_ts=?, last_error=?, updated_at=strftime('%Y-%m-%dT%H:%M:%f','now')
                WHERE job_id=?
                """,
                ("failed" if terminal else "retry", attempts + 1, next_attempt, error[:2000], job_id),
            )
            conn.execute(
                """
                UPDATE ledger_events
                SET semantic_status=?, semantic_error=?
                WHERE event_id=?
                """,
                ("failed" if terminal else "pending", error[:2000], event_id),
            )
