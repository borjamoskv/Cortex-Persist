import dataclasses
import logging
import sqlite3
import threading
from typing import Protocol

from babylon60.crypto.keys import KeyLifecycleManager, ZKSwarmIdentity
from babylon60.crypto.rekor_client import RekorClient
from babylon60.crypto.rfc3161 import RFC3161Client
from babylon60.ledger.models import LedgerEvent
from babylon60.ledger.queue import EnrichmentQueue
from babylon60.ledger.store import LedgerStore

logger = logging.getLogger("babylon60.ledger.writer")


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

        self.rekor_client = RekorClient()
        self.rfc3161_client = RFC3161Client()
        self.key_manager = KeyLifecycleManager()

    def _async_anchor(self, event_hash: str) -> None:
        """Background thread to anchor the hash to Rekor and FreeTSA."""
        try:
            # 1. Get current identity
            keypair = self.key_manager.get_or_create_identity()

            # 2. Sign the hash
            signature_b64 = ZKSwarmIdentity.sign_payload(event_hash, keypair.private_key_b64)

            # 3. Anchor to Rekor
            # Wait, Rekor takes a PEM. We will use the raw b64 as PEM content.
            # In a full implementation we'd format it as PEM properly.
            pem = f"-----BEGIN PUBLIC KEY-----\n{keypair.public_key_b64}\n-----END PUBLIC KEY-----"
            self.rekor_client.anchor_payload(event_hash, signature_b64, pem)

            # 4. Request RFC3161 Timestamp
            tsr = self.rfc3161_client.request_timestamp(event_hash)
            if tsr:
                logger.info("Successfully received RFC3161 timestamp for hash %s", event_hash)
        except Exception as e:  # noqa: BLE001
            logger.error("Async anchoring failed: %s", e)

    def append(self, event: LedgerEvent) -> str:
        if self.origin_policy is not None:
            self.origin_policy.validate_event(event)
        if self.replay_policy is not None:
            self.replay_policy.validate_event(event)

        with self.store.tx() as conn:
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

            from babylon60.database.core import causal_write

            with causal_write(conn):
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

        # Fire and forget external anchoring
        threading.Thread(target=self._async_anchor, args=(event.hash,), daemon=True).start()

        return event.event_id
