from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Optional

from cortex.ledger.models import ActionResult, ActionTarget, IntentPayload, LedgerEvent
from cortex.ledger.store import LedgerStore

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.ledger")


class LedgerVerifier:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    def verify_chain(self) -> dict:
        violations = []
        checked = 0
        stats = {"pending": 0, "processing": 0, "indexed": 0, "failed": 0}

        with self.store.tx() as conn:
            cursor = conn.execute(
                "SELECT event_id, payload_json, prev_hash, hash, semantic_status "
                "FROM ledger_events ORDER BY rowid ASC"
            )
            current_prev = "GENESIS"
            for row in cursor:
                checked += 1
                event_id = row["event_id"]
                payload = json.loads(row["payload_json"])
                p_hash = row["prev_hash"]
                c_hash = row["hash"]
                s_status = row["semantic_status"]

                if s_status in stats:
                    stats[s_status] += 1
                if s_status == "failed":
                    violations.append(f"Semantic enrichment failed for event {event_id}")

                if p_hash != current_prev:
                    violations.append(
                        f"Chain break at {event_id}: "
                        f"prev_hash is {p_hash}, but expected {current_prev}"
                    )

                # Full hash verification
                try:
                    event = self._reconstruct_event(payload)
                    recomputed = event.compute_hash(p_hash)
                    if recomputed != c_hash:
                        violations.append(
                            f"Hash mismatch at {event_id}: "
                            f"stored {c_hash}, recomputed {recomputed}"
                        )
                except Exception as e:
                    violations.append(f"Error parsing event {event_id}: {e}")

                current_prev = c_hash

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_events": checked,
            "enrichment_stats": stats,
        }

    def create_checkpoint(self, batch_size: int = 10) -> Optional[int]:
        from cortex.consensus.merkle import MerkleTree

        with self.store.tx() as conn:
            # 1. Find last event processed into a checkpoint
            cursor = conn.execute(
                "SELECT end_event_id FROM ledger_checkpoints ORDER BY checkpoint_id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            last_event_id = row[0] if row else None

            # 2. Get next batch of events
            where_clause = ""
            args = []
            if last_event_id:
                # Get the rowid of the last event to get following ones
                cursor = conn.execute(
                    "SELECT rowid FROM ledger_events WHERE event_id = ?", (last_event_id,)
                )
                r_id_row = cursor.fetchone()
                if r_id_row:
                    where_clause = "WHERE rowid > ?"
                    args = [r_id_row[0]]

            cursor = conn.execute(
                f"SELECT event_id, hash FROM ledger_events {where_clause} "
                "ORDER BY rowid ASC LIMIT ?",
                (*args, batch_size),
            )
            rows = cursor.fetchall()

            if len(rows) < batch_size:
                return None

            hashes = [r["hash"] for r in rows if r["hash"]]
            if not hashes:
                return None

            tree = MerkleTree(hashes)
            root_hash = tree.root

            start_ev = rows[0]["event_id"]
            end_ev = rows[-1]["event_id"]

            cursor = conn.execute(
                """
                INSERT INTO ledger_checkpoints
                (root_hash, start_event_id, end_event_id, event_count)
                VALUES (?, ?, ?, ?)
                """,
                (root_hash, start_ev, end_ev, len(hashes)),
            )
            return cursor.lastrowid

    def _reconstruct_event(self, payload: dict) -> LedgerEvent:
        # Helper to rebuild the event from the payload JSON
        target = ActionTarget(**payload["target"])
        result = ActionResult(**payload["result"])
        intent = IntentPayload(**payload["intent"]) if payload.get("intent") else None

        return LedgerEvent(
            event_id=payload["event_id"],
            ts=payload["timestamp"],
            tool=payload["tool"],
            actor=payload["actor"],
            action=payload["action"],
            target=target,
            result=result,
            intent=intent,
            correlation_id=payload.get("correlation_id"),
            trace_id=payload.get("trace_id"),
            prev_hash=payload.get("prev_hash"),
            hash=payload.get("hash"),
            semantic_status=payload.get("semantic_status", "pending"),
            metadata=payload.get("metadata", {}),
        )
