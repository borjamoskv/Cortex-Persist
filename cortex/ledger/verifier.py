# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from cortex.ledger.models import (
    ActionResult,
    ActionTarget,
    IntentPayload,
    LedgerEvent,
    LedgerOriginSignature,
)
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
                            f"Hash mismatch at {event_id}: stored {c_hash}, recomputed {recomputed}"
                        )
                except (ValueError, TypeError, OSError, KeyError) as e:
                    violations.append(f"Error parsing event {event_id}: {e}")

                current_prev = c_hash

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_events": checked,
            "enrichment_stats": stats,
        }

    def _get_mldsa_private_key(self):
        import base64
        import os

        from cryptography.hazmat.primitives.asymmetric import mldsa

        from cortex.crypto.aes import get_default_encrypter
        from cortex.crypto.keyring import keyring

        db_dir = os.path.dirname(self.store.db_path) if self.store.db_path else "."
        if not db_dir:
            db_dir = "."
        key_path = os.path.join(db_dir, "cortex_mldsa_sovereign.bin")
        encrypter = get_default_encrypter()

        seed = None

        # 1. Try to load from disk
        if os.path.exists(key_path):
            # Enforce chmod 600 permissions
            os.chmod(key_path, 0o600)

            with open(key_path, "rb") as key_file:
                content = key_file.read()

            if content.startswith(b"v6_aesgcm:"):
                decrypted_str = encrypter.decrypt_str(content.decode("utf-8"), tenant_id="default")
                if decrypted_str:
                    seed = base64.b64decode(decrypted_str)
            else:
                # Legacy raw format
                seed = content

                # If master key is active, migrate to encrypted format
                if encrypter.is_active:
                    seed_b64 = base64.b64encode(seed).decode("utf-8")
                    encrypted_str = encrypter.encrypt_str(seed_b64, tenant_id="default")
                    if encrypted_str:
                        with open(key_path, "wb") as key_file:
                            key_file.write(encrypted_str.encode("utf-8"))
                        os.chmod(key_path, 0o600)

        # 2. If not on disk, try to get from keyring
        if seed is None:
            if keyring is not None and not os.environ.get("CORTEX_TESTING"):
                try:
                    keyring_b64 = keyring.get_password("cortex_v6", "mldsa_sovereign_seed")
                    if keyring_b64:
                        seed = base64.b64decode(keyring_b64)
                        # Write to disk
                        os.makedirs(db_dir, exist_ok=True)
                        if encrypter.is_active:
                            seed_b64 = base64.b64encode(seed).decode("utf-8")
                            encrypted_str = encrypter.encrypt_str(seed_b64, tenant_id="default")
                            if encrypted_str:
                                with open(key_path, "wb") as key_file:
                                    key_file.write(encrypted_str.encode("utf-8"))
                        else:
                            with open(key_path, "wb") as key_file:
                                key_file.write(seed)
                        os.chmod(key_path, 0o600)
                except (ValueError, TypeError, OSError, KeyError):
                    pass

        # 3. If still not found, generate new key
        if seed is None:
            private_key = mldsa.MLDSA44PrivateKey.generate()
            seed = private_key.private_bytes_raw()

            # Vault in keyring if available
            if keyring is not None and not os.environ.get("CORTEX_TESTING"):
                try:
                    seed_b64 = base64.b64encode(seed).decode("utf-8")
                    keyring.set_password("cortex_v6", "mldsa_sovereign_seed", seed_b64)
                except (ValueError, TypeError, OSError, KeyError):
                    pass

            # Write to disk
            os.makedirs(db_dir, exist_ok=True)
            if encrypter.is_active:
                seed_b64 = base64.b64encode(seed).decode("utf-8")
                encrypted_str = encrypter.encrypt_str(seed_b64, tenant_id="default")
                if encrypted_str:
                    with open(key_path, "wb") as key_file:
                        key_file.write(encrypted_str.encode("utf-8"))
            else:
                with open(key_path, "wb") as key_file:
                    key_file.write(seed)
            os.chmod(key_path, 0o600)
            return private_key

        return mldsa.MLDSA44PrivateKey.from_seed_bytes(seed)

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
                    mldsa_signature TEXT,
                    mldsa_public_key TEXT,
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

            # Post-Quantum ML-DSA Signature of Checkpoint Root
            pk = self._get_mldsa_private_key()
            pub = pk.public_key()
            sig_payload = f"{root_hash}_{start_ev}_{end_ev}_{len(hashes)}".encode()
            sig = pk.sign(sig_payload)
            sig_hex = sig.hex()
            pub_hex = pub.public_bytes_raw().hex()

            cursor = conn.execute(
                """
                INSERT INTO ledger_checkpoints
                (root_hash, start_event_id, end_event_id, event_count, mldsa_signature, mldsa_public_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (root_hash, start_ev, end_ev, len(hashes), sig_hex, pub_hex),
            )
            return cursor.lastrowid

    def _reconstruct_event(self, payload: dict) -> LedgerEvent:
        # Helper to rebuild the event from the payload JSON
        target = ActionTarget(**payload["target"])
        result = ActionResult(**payload["result"])
        intent = IntentPayload(**payload["intent"]) if payload.get("intent") else None
        origin = (
            LedgerOriginSignature(**payload["origin"])
            if isinstance(payload.get("origin"), dict)
            else None
        )

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
            origin=origin,
            prev_hash=payload.get("prev_hash"),
            hash=payload.get("hash"),
            semantic_status=payload.get("semantic_status", "pending"),
            metadata=payload.get("metadata", {}),
        )

    def verify_checkpoint_signatures(self) -> dict:
        """Verify the ML-DSA post-quantum signature of all checkpoints."""
        violations = []
        checked = 0
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import mldsa

        with self.store.tx() as conn:
            # Check if columns exist
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(ledger_checkpoints)").fetchall()
            }
            if "mldsa_signature" not in columns or "mldsa_public_key" not in columns:
                return {
                    "valid": True,
                    "violations": ["MLDSA signature columns not initialized yet."],
                    "checked_checkpoints": 0,
                }

            cursor = conn.execute(
                "SELECT checkpoint_id, root_hash, start_event_id, end_event_id, event_count, mldsa_signature, mldsa_public_key "
                "FROM ledger_checkpoints ORDER BY checkpoint_id ASC"
            )
            for row in cursor:
                checked += 1
                c_id = row["checkpoint_id"]
                root_hash = row["root_hash"]
                start_ev = row["start_event_id"]
                end_ev = row["end_event_id"]
                count = row["event_count"]
                sig_hex = row["mldsa_signature"]
                pub_hex = row["mldsa_public_key"]

                if not sig_hex or not pub_hex:
                    violations.append(
                        f"Checkpoint {c_id} is missing post-quantum signature or public key."
                    )
                    continue

                try:
                    pubkey_bytes = bytes.fromhex(pub_hex)
                    sig_bytes = bytes.fromhex(sig_hex)
                    pubkey = mldsa.MLDSA44PublicKey.from_public_bytes(pubkey_bytes)

                    sig_payload = f"{root_hash}_{start_ev}_{end_ev}_{count}".encode()
                    pubkey.verify(sig_bytes, sig_payload)
                except InvalidSignature:
                    violations.append(f"Invalid ML-DSA signature for checkpoint {c_id}.")
                except (ValueError, TypeError, OSError, KeyError) as e:
                    violations.append(f"Error validating checkpoint {c_id}: {e}")

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_checkpoints": checked,
        }

    def verify_post_quantum(self) -> dict:
        """Performs a comprehensive verification including both classical chain hashes and ML-DSA checkpoint signatures."""
        chain_report = self.verify_chain()
        checkpoint_report = self.verify_checkpoint_signatures()

        combined_violations = list(chain_report.get("violations", [])) + list(
            checkpoint_report.get("violations", [])
        )

        return {
            "valid": len(combined_violations) == 0,
            "violations": combined_violations,
            "checked_events": chain_report.get("checked_events", 0),
            "checked_checkpoints": checkpoint_report.get("checked_checkpoints", 0),
            "enrichment_stats": chain_report.get("enrichment_stats", {}),
        }
