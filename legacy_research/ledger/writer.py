# [C5-REAL] Exergy-Maximized
import dataclasses
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
from typing import Protocol

from legacy_research.ledger.models import LedgerEvent
from legacy_research.ledger.queue import EnrichmentQueue
from legacy_research.ledger.store import LedgerStore


class _OriginSignaturePolicy(Protocol):
    def validate_event(self, event: LedgerEvent) -> None: ...


class _ReplayAdmissionResult(Protocol):
    status: str
    event_id: str


class _ReplayAdmissionPolicy(Protocol):
    def validate_event(self, event: LedgerEvent) -> None: ...

    def admit_event(
        self,
        conn: sqlite3.Connection,
        event: LedgerEvent,
    ) -> _ReplayAdmissionResult: ...


class LedgerWriter:
    def __init__(
        self,
        store: LedgerStore,
        queue: EnrichmentQueue,
        *,
        origin_policy: _OriginSignaturePolicy | None = None,
        replay_policy: _ReplayAdmissionPolicy | None = None,
    ) -> None:
        self.store = store
        self.queue = queue
        self.origin_policy = origin_policy
        self.replay_policy = replay_policy

    def append(self, event: LedgerEvent) -> str:
        if self.origin_policy is not None:
            self.origin_policy.validate_event(event)
        if self.replay_policy is not None:
            self.replay_policy.validate_event(event)

        with self.store.tx(mode="EXCLUSIVE") as conn:
            if self.replay_policy is not None:
                admission = self.replay_policy.admit_event(conn, event)
                if admission.status == "idempotent":
                    return admission.event_id

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
