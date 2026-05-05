import dataclasses
import sqlite3

from cortex.ledger.models import LedgerEvent
from cortex.ledger.origin import OriginSignaturePolicy
from cortex.ledger.pii import LedgerPIIPolicy
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.replay import ReplayProtectionError, ReplayProtectionPolicy
from cortex.ledger.store import LedgerStore, LedgerStoreError


class LedgerWriter:
    def __init__(
        self,
        store: LedgerStore,
        queue: EnrichmentQueue,
        origin_policy: OriginSignaturePolicy | None = None,
        replay_policy: ReplayProtectionPolicy | None = None,
        pii_policy: LedgerPIIPolicy | None = None,
    ) -> None:
        if replay_policy is not None and origin_policy is None:
            raise ValueError("replay_policy_requires_origin_policy")
        self.store = store
        self.queue = queue
        self.origin_policy = origin_policy
        self.replay_policy = replay_policy
        self.pii_policy = pii_policy

    def append(self, event: LedgerEvent) -> str:
        if self.pii_policy is not None:
            self.pii_policy.validate_event(event)
        if self.origin_policy is not None:
            self.origin_policy.validate_event(event)
        if self.replay_policy is not None:
            self.replay_policy.validate_freshness(event)
            return self._append_with_replay_protection(event)

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

    def _append_with_replay_protection(self, event: LedgerEvent) -> str:
        assert self.replay_policy is not None
        conn = self.store.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if self.replay_policy.is_idempotent_retry(conn, event):
                conn.commit()
                return event.event_id

            cursor = conn.execute("SELECT hash FROM ledger_events ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row["hash"] if row else "GENESIS"

            new_hash = event.compute_hash(prev_hash)
            event = dataclasses.replace(event, prev_hash=prev_hash, hash=new_hash)
            self.replay_policy.reserve(conn, event)

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
            conn.commit()
        except ReplayProtectionError:
            conn.rollback()
            raise
        except sqlite3.Error as exc:
            conn.rollback()
            raise LedgerStoreError(str(exc)) from exc
        finally:
            conn.close()

        self.queue.enqueue(event.event_id)
        return event.event_id
