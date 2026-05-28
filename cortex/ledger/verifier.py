from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from cortex.ledger.models import ActionResult, ActionTarget, IntentPayload, LedgerEvent
from cortex.ledger.store import LedgerStore
from cortex.utils.canonical import compute_fact_hash, compute_tx_hash, compute_tx_hash_v1

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.ledger")


class LedgerVerifier:
    def __init__(self, store: LedgerStore) -> None:
        self.store = store

    @staticmethod
    def _table_exists(conn, table_name: str) -> bool:
        cursor = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'virtual table') AND name = ?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    @staticmethod
    def _table_columns(conn, table_name: str) -> set[str]:
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})")}

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
                            f"Hash mismatch at {event_id}: stored {c_hash}, recomputed {recomputed}"
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

    def verify_all(self) -> dict:
        """Verify every known ledger surface in one report.

        Covers the event ledger, event checkpoints, fact transaction chain,
        transaction Merkle checkpoints, and fact content hashes when decryptable.
        """
        sections = {
            "ledger_events": self.verify_chain(),
            "ledger_checkpoints": self.verify_event_checkpoints(),
            "transactions": self.verify_transactions(),
            "merkle_roots": self.verify_transaction_checkpoints(),
            "facts_hash": self.verify_fact_hashes(),
        }
        valid = all(section.get("valid", False) for section in sections.values())
        return {
            "valid": valid,
            "sections": sections,
            "violations": {
                name: section.get("violations", [])
                for name, section in sections.items()
                if section.get("violations")
            },
        }

    def verify_transactions(self) -> dict:
        """Verify the tenant-scoped facts transaction hash chain."""
        violations: list[str] = []
        checked = 0
        tenants: dict[str, int] = {}

        with self.store.tx() as conn:
            if not self._table_exists(conn, "transactions"):
                return {
                    "valid": False,
                    "violations": ["Missing table: transactions"],
                    "checked_transactions": 0,
                    "tenants": {},
                }

            columns = self._table_columns(conn, "transactions")
            has_tenant = "tenant_id" in columns
            tenant_expr = "tenant_id" if has_tenant else "'default' AS tenant_id"
            cursor = conn.execute(
                "SELECT id, project, action, detail, prev_hash, hash, timestamp, "
                f"{tenant_expr} FROM transactions ORDER BY tenant_id, id"
            )

            expected_prev_by_tenant: dict[str, str] = {}
            for row in cursor:
                checked += 1
                tx_id = row["id"]
                tenant_id = row["tenant_id"] or "default"
                tenants[tenant_id] = tenants.get(tenant_id, 0) + 1

                prev_hash = row["prev_hash"]
                expected_prev = expected_prev_by_tenant.get(tenant_id, "GENESIS")
                if prev_hash != expected_prev:
                    violations.append(
                        f"Transaction chain break at tx {tx_id} tenant {tenant_id}: "
                        f"prev_hash is {prev_hash}, expected {expected_prev}"
                    )

                detail_json = row["detail"] if row["detail"] is not None else "{}"
                recomputed = compute_tx_hash(
                    prev_hash,
                    row["project"],
                    row["action"],
                    detail_json,
                    row["timestamp"],
                )
                if recomputed != row["hash"]:
                    legacy = compute_tx_hash_v1(
                        prev_hash,
                        row["project"],
                        row["action"],
                        detail_json,
                        row["timestamp"],
                    )
                    if legacy != row["hash"]:
                        violations.append(
                            f"Transaction hash mismatch at tx {tx_id}: "
                            f"stored {row['hash']}, recomputed {recomputed}"
                        )

                expected_prev_by_tenant[tenant_id] = row["hash"]

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_transactions": checked,
            "tenants": tenants,
        }

    def verify_transaction_checkpoints(self) -> dict:
        """Verify Merkle checkpoints over the facts transaction ledger."""
        violations: list[str] = []
        checked = 0

        with self.store.tx() as conn:
            if not self._table_exists(conn, "merkle_roots"):
                return {
                    "valid": False,
                    "violations": ["Missing table: merkle_roots"],
                    "checked_checkpoints": 0,
                }
            if not self._table_exists(conn, "transactions"):
                return {
                    "valid": False,
                    "violations": ["Missing table: transactions"],
                    "checked_checkpoints": 0,
                }

            from cortex.consensus.merkle import MerkleTree

            cursor = conn.execute(
                "SELECT id, root_hash, tx_start_id, tx_end_id, tx_count "
                "FROM merkle_roots ORDER BY id"
            )
            for row in cursor:
                checked += 1
                hashes = [
                    tx["hash"]
                    for tx in conn.execute(
                        "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                        (row["tx_start_id"], row["tx_end_id"]),
                    )
                ]
                if len(hashes) != row["tx_count"]:
                    violations.append(
                        f"Transaction checkpoint {row['id']} count mismatch: "
                        f"stored {row['tx_count']}, recomputed {len(hashes)}"
                    )
                if not hashes:
                    violations.append(f"Transaction checkpoint {row['id']} covers no transactions")
                    continue
                recomputed = MerkleTree(hashes).root
                if recomputed != row["root_hash"]:
                    violations.append(
                        f"Transaction checkpoint {row['id']} root mismatch: "
                        f"stored {row['root_hash']}, recomputed {recomputed}"
                    )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_checkpoints": checked,
        }

    def verify_event_checkpoints(self) -> dict:
        """Verify Merkle checkpoints over ledger_events."""
        violations: list[str] = []
        checked = 0

        with self.store.tx() as conn:
            if not self._table_exists(conn, "ledger_checkpoints"):
                return {
                    "valid": False,
                    "violations": ["Missing table: ledger_checkpoints"],
                    "checked_checkpoints": 0,
                }
            if not self._table_exists(conn, "ledger_events"):
                return {
                    "valid": False,
                    "violations": ["Missing table: ledger_events"],
                    "checked_checkpoints": 0,
                }

            from cortex.consensus.merkle import MerkleTree

            cursor = conn.execute(
                "SELECT checkpoint_id, root_hash, start_event_id, end_event_id, event_count "
                "FROM ledger_checkpoints ORDER BY checkpoint_id"
            )
            for row in cursor:
                checked += 1
                start_row = conn.execute(
                    "SELECT rowid FROM ledger_events WHERE event_id = ?", (row["start_event_id"],)
                ).fetchone()
                end_row = conn.execute(
                    "SELECT rowid FROM ledger_events WHERE event_id = ?", (row["end_event_id"],)
                ).fetchone()
                if start_row is None or end_row is None:
                    violations.append(
                        f"Event checkpoint {row['checkpoint_id']} references missing events"
                    )
                    continue

                hashes = [
                    event["hash"]
                    for event in conn.execute(
                        "SELECT hash FROM ledger_events WHERE rowid >= ? AND rowid <= ? "
                        "ORDER BY rowid",
                        (start_row["rowid"], end_row["rowid"]),
                    )
                ]
                if len(hashes) != row["event_count"]:
                    violations.append(
                        f"Event checkpoint {row['checkpoint_id']} count mismatch: "
                        f"stored {row['event_count']}, recomputed {len(hashes)}"
                    )
                if not hashes:
                    violations.append(f"Event checkpoint {row['checkpoint_id']} covers no events")
                    continue
                recomputed = MerkleTree(hashes).root
                if recomputed != row["root_hash"]:
                    violations.append(
                        f"Event checkpoint {row['checkpoint_id']} root mismatch: "
                        f"stored {row['root_hash']}, recomputed {recomputed}"
                    )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_checkpoints": checked,
        }

    def verify_fact_hashes(self) -> dict:
        """Verify facts.hash against plaintext when content is decryptable."""
        violations: list[str] = []
        checked = 0

        with self.store.tx() as conn:
            if not self._table_exists(conn, "facts"):
                return {
                    "valid": True,
                    "skipped": True,
                    "reason": "Missing table: facts",
                    "violations": [],
                    "checked_facts": 0,
                }

            columns = self._table_columns(conn, "facts")
            required = {"id", "content", "hash"}
            if not required.issubset(columns):
                missing = ", ".join(sorted(required - columns))
                return {
                    "valid": False,
                    "violations": [f"facts table missing required columns: {missing}"],
                    "checked_facts": 0,
                }

            has_tenant = "tenant_id" in columns
            tenant_expr = "tenant_id" if has_tenant else "'default' AS tenant_id"
            cursor = conn.execute(
                f"SELECT id, content, hash, {tenant_expr} FROM facts WHERE hash IS NOT NULL ORDER BY id"
            )

            encrypter = None
            for row in cursor:
                content = row["content"]
                tenant_id = row["tenant_id"] or "default"
                if content is None:
                    continue

                plaintext = content
                if isinstance(content, str) and content.startswith("v6_aesgcm:"):
                    try:
                        if encrypter is None:
                            from cortex.crypto import get_default_encrypter

                            encrypter = get_default_encrypter()
                        plaintext = encrypter.decrypt_str(content, tenant_id=tenant_id)
                    except RuntimeError as exc:
                        return {
                            "valid": True,
                            "skipped": True,
                            "reason": str(exc),
                            "violations": [],
                            "checked_facts": checked,
                        }
                    except ValueError as exc:
                        violations.append(f"Fact {row['id']} decrypt failed: {exc}")
                        continue

                checked += 1
                if compute_fact_hash(plaintext or "") != row["hash"]:
                    violations.append(f"Fact hash mismatch at fact {row['id']}")

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_facts": checked,
        }

    def create_checkpoint(self, batch_size: int = 10) -> int | None:
        from cortex.consensus.merkle import MerkleTree

        with self.store.tx() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger_checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_hash TEXT NOT NULL,
                    start_event_id TEXT NOT NULL,
                    end_event_id TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )
                """
            )

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
