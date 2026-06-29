"""
Enterprise Audit Ledger (SOC 2 Compliance).

Append-only cryptographic ledger tracking all operations.
Secures the `tenant_id` and the identity of the operator, creating
a hash-chain to prove immutability of the audit logs.
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from babylon60.audit.smt import smt_engine
from babylon60.crypto.hash_registry import cortex_hash
from babylon60.database.core import causal_write

logger = logging.getLogger("cortex.audit.ledger")

_CREATE_AUDIT_SQL = """
CREATE TABLE IF NOT EXISTS security_audit_log (
    audit_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    status TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    signature TEXT NOT NULL,
    external_anchor TEXT
);
"""


import asyncio
import fcntl


class AsyncFileLock:
    """Non-blocking asynchronous cross-process file lock using fcntl."""

    def __init__(self, lock_path: str = "/tmp/cortex_audit_ledger.lock") -> None:
        self.lock_path = lock_path
        self.fp = None

    async def __aenter__(self) -> "AsyncFileLock":
        self.fp = open(self.lock_path, "w")
        while True:
            try:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                await asyncio.sleep(0.01)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.fp:
            try:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            finally:
                self.fp.close()
                self.fp = None


class EnterpriseAuditLedger:
    """Immutable Audit Ledger for enterprise-grade SOC 2 compliance (Merkle Micro-Batched)."""

    __slots__ = (
        "_conn",
        "_last_hash",
        "_ready",
        "private_key",
        "public_key",
        "_lock",
        "_batch_queue",
        "_batch_task",
        "batch_window_ms",
        "max_batch_size",
        "_km",
        "actor_id",
    )

    def __init__(self, conn: aiosqlite.Connection) -> None:
        import asyncio

        self._conn = conn
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

        self._batch_queue: list[tuple[dict[str, Any], asyncio.Future[str]]] = []
        self._batch_task: asyncio.Task | None = None

        # Configure thresholds
        self.batch_window_ms = int(os.environ.get("CORTEX_LEDGER_BATCH_MS", "50"))
        self.max_batch_size = int(os.environ.get("CORTEX_LEDGER_MAX_BATCH", "500"))

        # C5-REAL Sovereign Ed25519 Keypair (Enterprise Key Management)
        from babylon60.crypto.keys import KeyManager

        self._km = KeyManager(service_name="cortex_ledger_enterprise")
        self.actor_id = "ledger_master"

        priv_b64 = self._km.get_private_key_b64(self.actor_id)
        if not priv_b64:
            self._km.generate_and_store_key(self.actor_id)
            priv_b64 = self._km.get_private_key_b64(self.actor_id)

        priv_bytes = __import__("base64").b64decode(priv_b64)
        try:
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        except ValueError:
            key = serialization.load_pem_private_key(priv_bytes, password=None)
            if not isinstance(key, ed25519.Ed25519PrivateKey):
                raise ValueError("[C5-REAL] FATAL: Ledger Identity must be strictly Ed25519.")
            self.private_key = key

        self.public_key = self.private_key.public_key()

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            async with AsyncFileLock():
                if self._ready:
                    return
                await self._conn.execute(_CREATE_AUDIT_SQL)

                try:
                    await self._conn.execute(
                        "ALTER TABLE security_audit_log ADD COLUMN external_anchor TEXT"
                    )
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        raise e

                await self._conn.commit()
                cursor = await self._conn.execute(
                    "SELECT prev_hash, signature FROM security_audit_log ORDER BY rowid DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                if row:
                    prev_hash, sig = row[0], row[1]
                    # Reconstruct the last batch using its signature to compute its entry_hash
                    cursor2 = await self._conn.execute(
                        "SELECT audit_id FROM security_audit_log WHERE signature = ? ORDER BY rowid ASC",
                        (sig,),
                    )
                    rows2 = await cursor2.fetchall()
                    batch_audit_ids = [r[0] for r in rows2]

                    for audit_id in batch_audit_ids:
                        smt_engine.update(cortex_hash(audit_id.encode()), audit_id)

                    merkle_root = smt_engine.root
                    self._last_hash = cortex_hash(
                        f"merkle_batch:{merkle_root}:{prev_hash}".encode()
                    )
                else:
                    self._last_hash = "GENESIS"
                self._ready = True

    async def close(self) -> None:
        if self._batch_task is not None:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except (asyncio.CancelledError, Exception):
                pass
            self._batch_task = None

    async def verify_chain(self) -> dict[str, Any]:
        """Perform a full verification of the cryptographic chain.
        Returns {'status': 'verified'} if pristine, or {'status': 'tampered', 'corrupted_audit_id': id} if broken.
        """
        import json

        await self.ensure_table()

        # [C5-REAL] Verify pinned public key from environment/config if present
        pinned_pub_pem = os.environ.get("CORTEX_LEDGER_PUBLIC_KEY")
        if pinned_pub_pem:
            try:
                pinned_bytes = pinned_pub_pem.encode("utf-8")
                if b"PUBLIC KEY" in pinned_bytes:
                    pinned_key = serialization.load_pem_public_key(pinned_bytes)
                else:
                    pinned_key = ed25519.Ed25519PublicKey.from_public_bytes(
                        bytes.fromhex(pinned_pub_pem)
                    )

                my_bytes = self.public_key.public_bytes(
                    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
                )
                pinned_raw_bytes = pinned_key.public_bytes(
                    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
                )
                if my_bytes != pinned_raw_bytes:
                    return {
                        "status": "tampered",
                        "corrupted_audit_id": "GENESIS",
                        "reason": "ledger_public_key_mismatch",
                    }
            except Exception as e:
                logger.error("Failed to verify pinned ledger public key: %s", e)
                return {
                    "status": "tampered",
                    "corrupted_audit_id": "GENESIS",
                    "reason": f"invalid_pinned_public_key: {e}",
                }

        async with self._conn.execute(
            "SELECT rowid, audit_id, timestamp, tenant_id, actor_role, actor_id, action, resource, status, prev_hash, signature, external_anchor FROM security_audit_log ORDER BY rowid ASC"
        ) as cursor:
            rows = list(await cursor.fetchall())

        if not rows:
            return {"status": "verified", "blocks": 0}

        # Group by batch (same prev_hash and signature)
        batches: list[tuple[str, str, list[dict]]] = []
        current_batch: list[dict] = []
        current_prev_hash = rows[0]["prev_hash"]
        current_sig = rows[0]["signature"]

        for row in rows:
            # Validate individual audit_id to detect row-level tampering
            expected_audit_id_v2 = cortex_hash(
                f"{row['timestamp']}|{row['tenant_id']}|{row['actor_role']}|{row['actor_id']}|{row['action']}|{row['resource']}|{row['status']}".encode()
            )
            expected_audit_id_v1 = cortex_hash(
                f"{row['timestamp']}{row['tenant_id']}{row['actor_role']}{row['actor_id']}{row['action']}{row['resource']}{row['status']}".encode()
            )
            if row["audit_id"] not in (expected_audit_id_v2, expected_audit_id_v1):
                return {
                    "status": "tampered",
                    "corrupted_audit_id": row["audit_id"],
                    "reason": "row_hash_mismatch",
                }

            if row["prev_hash"] == current_prev_hash and row["signature"] == current_sig:
                current_batch.append(row)
            else:
                batches.append((current_prev_hash, current_sig, current_batch))
                current_prev_hash = row["prev_hash"]
                current_sig = row["signature"]
                current_batch = [row]

        if current_batch:
            batches.append((current_prev_hash, current_sig, current_batch))

        # Verify Merkle chain and signatures
        expected_prev_hash = "GENESIS"
        from babylon60.audit.smt import SparseMerkleTree

        local_smt = SparseMerkleTree()

        for prev_hash, signature, batch_rows in batches:
            if prev_hash != expected_prev_hash:
                return {
                    "status": "tampered",
                    "corrupted_audit_id": batch_rows[0]["audit_id"],
                    "reason": f"chain_broken (expected {expected_prev_hash}, got {prev_hash})",
                }

            # Check if this batch is a COMPACTION_NODE
            if len(batch_rows) == 1 and batch_rows[0]["action"] == "COMPACTION_NODE":
                row = batch_rows[0]
                compaction_payload = (
                    f"COMPACTION:{row['prev_hash']}:{row['status']}:{row['resource']}"
                )
                try:
                    self.public_key.verify(bytes.fromhex(signature), compaction_payload.encode())
                except InvalidSignature:
                    return {
                        "status": "tampered",
                        "corrupted_audit_id": row["audit_id"],
                        "reason": "invalid_compaction_signature",
                    }
                expected_prev_hash = row["status"]
                continue

            batch_audit_ids = [r["audit_id"] for r in batch_rows]
            for aid in batch_audit_ids:
                local_smt.update(cortex_hash(aid.encode()), aid)
            merkle_root = local_smt.root

            entry_hash_payload = f"merkle_batch:{merkle_root}:{prev_hash}"
            entry_hash = cortex_hash(entry_hash_payload.encode())

            try:
                self.public_key.verify(bytes.fromhex(signature), entry_hash.encode())
            except InvalidSignature:
                return {
                    "status": "tampered",
                    "corrupted_audit_id": batch_rows[0]["audit_id"],
                    "reason": "invalid_signature",
                }

            # [C5-REAL] Verify external Rekor/TSA anchor if requested and present
            if os.environ.get("CORTEX_VERIFY_EXTERNAL_ANCHORS") == "true":
                row = batch_rows[0]
                if len(row) > 11 and row["external_anchor"]:
                    try:
                        anchor_data = json.loads(row["external_anchor"])
                        rekor_uuid = anchor_data.get("rekor_uuid")
                        if rekor_uuid and rekor_uuid != "mock_rekor":
                            from babylon60.audit.rekor_client import RekorClient

                            rekor_client = RekorClient()
                            try:
                                rekor_entry = await rekor_client.verify_entry(rekor_uuid)
                                if not rekor_entry:
                                    return {
                                        "status": "tampered",
                                        "corrupted_audit_id": row["audit_id"],
                                        "reason": f"rekor_anchor_missing (uuid {rekor_uuid})",
                                    }
                                log_entry_data = list(rekor_entry.values())[0]
                                body_b64 = log_entry_data.get("body")
                                if body_b64:
                                    import base64

                                    body_data = json.loads(
                                        base64.b64decode(body_b64).decode("utf-8")
                                    )
                                    logged_hash = (
                                        body_data.get("spec", {})
                                        .get("data", {})
                                        .get("hash", {})
                                        .get("value")
                                    )
                                    if logged_hash != entry_hash:
                                        return {
                                            "status": "tampered",
                                            "corrupted_audit_id": row["audit_id"],
                                            "reason": f"rekor_hash_mismatch (expected {entry_hash}, got {logged_hash})",
                                        }
                            finally:
                                await rekor_client.close()
                    except Exception as e:
                        logger.error("Failed to verify external Rekor anchor: %s", e)

            expected_prev_hash = entry_hash

        return {"status": "verified", "blocks": len(batches)}

    async def _anchor_worker(self) -> None:
        """Background worker that pulls unanchored local entries and anchors them to Rekor/TSA asynchronously."""
        import asyncio
        import base64
        import json
        import sqlite3

        import httpx

        try:
            import rfc3161ng  # pyright: ignore[reportMissingImports] # Opt-in  # pyright: ignore[reportMissingImports] # Opt-in secure dependency
        except ImportError:
            rfc3161ng = None
            logger.warning(
                "rfc3161ng is not installed. TSA signatures will be disabled. Run pip install cortex-persist[secure]"
            )
        from cryptography.hazmat.primitives import serialization

        from babylon60.audit.rekor_client import RekorClient

        # C5-REAL Exergy Optimization: Instantiate external clients once outside the loop.
        rekor_client = RekorClient()
        tsa_url = "http://timestamp.digicert.com"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as http_client:
                while True:
                    await asyncio.sleep(self.batch_window_ms / 1000.0)
                    async with self._lock:
                        async with AsyncFileLock():
                            # Pull-Model: Fetch unanchored records from SQLite
                            try:
                                cursor = await self._conn.execute(
                                    "SELECT audit_id, signature, prev_hash FROM security_audit_log WHERE external_anchor IS NULL ORDER BY rowid ASC LIMIT ?",
                                    (self.max_batch_size,),
                                )
                                unanchored = await cursor.fetchall()
                            except (
                                sqlite3.ProgrammingError,
                                aiosqlite.ProgrammingError,
                                ValueError,
                                AttributeError,
                                RuntimeError,
                            ) as db_err:
                                logger.info(
                                    "[AuditLedger] SQLite connection closed or inactive during anchor run: %s",
                                    db_err,
                                )
                                self._batch_task = None
                                break

                            if not unanchored:
                                self._batch_task = None
                                break

                            for audit_id, signature, prev_hash in unanchored:
                                external_anchor = None
                                try:
                                    from babylon60.audit.smt import SparseMerkleTree

                                    smt_state = SparseMerkleTree()
                                    smt_state.update(cortex_hash(audit_id.encode()), audit_id)
                                    merkle_root = smt_state.root

                                    entry_hash = cortex_hash(
                                        f"merkle_batch:{merkle_root}:{prev_hash}".encode()
                                    )

                                    pub_pem = self.public_key.public_bytes(
                                        encoding=serialization.Encoding.PEM,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                                    )

                                    if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get(
                                        "CORTEX_TEST_ENV"
                                    ):
                                        rekor_uuid = "mock_rekor"
                                        rfc_token = "mock_rfc"
                                    else:
                                        # Asynchronous Rekor logging
                                        rekor_uuid = await rekor_client.log_entry(
                                            entry_hash, signature, pub_pem
                                        )  # pyright: ignore[reportArgumentType]

                                        tsa_signature = None
                                        if rfc3161ng is not None:
                                            try:
                                                tsa_req = rfc3161ng.make_request(
                                                    merkle_root.encode("utf-8")
                                                )
                                                tsa_resp = await http_client.post(
                                                    tsa_url,
                                                    content=tsa_req,
                                                    headers={
                                                        "Content-Type": "application/timestamp-query"
                                                    },
                                                )
                                                if tsa_resp.status_code == 200:
                                                    tsa_signature = base64.b64encode(
                                                        tsa_resp.content
                                                    ).decode("utf-8")
                                            except (
                                                ValueError,
                                                TypeError,
                                                KeyError,
                                                OSError,
                                                RuntimeError,
                                            ) as exc:
                                                logger.warning("TSA stamping failed: %s", exc)
                                        rfc_token = tsa_signature

                                    if rekor_uuid or rfc_token:
                                        external_anchor = json.dumps(
                                            {"rekor_uuid": rekor_uuid, "rfc3161_token": rfc_token}
                                        )

                                        # Update the row with the external anchor
                                        in_tx_before = self._conn.in_transaction
                                        with causal_write(self._conn):
                                            await self._conn.execute(
                                                "UPDATE security_audit_log SET external_anchor = ? WHERE audit_id = ?",
                                                (external_anchor, audit_id),
                                            )
                                            if not in_tx_before:
                                                await self._conn.commit()
                                except Exception as e:
                                    logger.error("[AuditLedger] External anchoring failed: %s", e)
        except Exception as general_err:
            logger.error(
                "[AuditLedger] Unexpected exception in anchor worker loop: %s", general_err
            )
        finally:
            await rekor_client.close()

    async def log_action(
        self,
        tenant_id: str,
        actor_role: str,
        actor_id: str,
        action: str,
        resource: str,
        status: str = "SUCCESS",
    ) -> str:
        """Securely logs an action synchronously within the SAGA boundary."""
        import asyncio

        await self.ensure_table()

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        audit_id = cortex_hash(
            f"{timestamp}|{tenant_id}|{actor_role}|{actor_id}|{action}|{resource}|{status}".encode()
        )

        in_tx_before = self._conn.in_transaction

        async with self._lock:
            async with AsyncFileLock():
                # 1. Fetch the actual last hash from DB to support transparent rollbacks
                cursor = await self._conn.execute(
                    "SELECT prev_hash, signature FROM security_audit_log ORDER BY rowid DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                if row:
                    prev_hash_db, sig_db = row[0], row[1]
                    cursor2 = await self._conn.execute(
                        "SELECT audit_id FROM security_audit_log WHERE signature = ? ORDER BY rowid ASC",
                        (sig_db,),
                    )
                    rows2 = await cursor2.fetchall()
                    batch_audit_ids = [r[0] for r in rows2]

                    # Reconstruct Sparse Merkle Tree state for current batch
                    for aid in batch_audit_ids:
                        smt_engine.update(cortex_hash(aid.encode()), aid)

                    merkle_root = smt_engine.root
                    current_last_hash = cortex_hash(
                        f"merkle_batch:{merkle_root}:{prev_hash_db}".encode()
                    )
                else:
                    current_last_hash = "GENESIS"

                # 2. Compute the new block via SMT inclusion
                smt_engine.update(cortex_hash(audit_id.encode()), audit_id)
                merkle_root_new = smt_engine.root
                entry_hash = cortex_hash(
                    f"merkle_batch:{merkle_root_new}:{current_last_hash}".encode()
                )
                signature = self.private_key.sign(entry_hash.encode()).hex()

                # 3. Insert synchronously inside the existing transaction
                with causal_write(self._conn):
                    await self._conn.execute(
                        """INSERT INTO security_audit_log
                           (audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                            resource, status, prev_hash, signature, external_anchor)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            audit_id,
                            timestamp,
                            tenant_id,
                            actor_role,
                            actor_id,
                            action,
                            resource,
                            status,
                            current_last_hash,
                            signature,
                            None,
                        ),
                    )
                    # Auto-commit ONLY if we are not inside a larger transaction
                    if not in_tx_before:
                        await self._conn.commit()

                self._last_hash = entry_hash

                # Trigger anchor worker if not running
                if self._batch_task is None:
                    self._batch_task = asyncio.create_task(self._anchor_worker())

        return audit_id

    def verify_zk_seal(self, payload: str, signature_hex: str) -> bool:
        """Verifies a cryptographic seal against the Audit Sovereign public key."""
        try:
            self.public_key.verify(bytes.fromhex(signature_hex), payload.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False

    def generate_ouroboros_seal(self, payload: str) -> str:
        """[C5-REAL] Generate an Ouroboros-specific cryptographic seal for autonomous L2/L3 mutations."""
        seal_payload = f"OUROBOROS-∞:{payload}"
        return self.private_key.sign(seal_payload.encode()).hex()

    def verify_batch(
        self, batch_audit_ids: list[str], prev_hash: str, signature_hex: str, smt_state: Any = None
    ) -> bool:
        """Verifies the cryptographic seal of a batch against the public key using entry_hash."""
        try:
            # Reconstruct batch entry_hash
            if smt_state is None:
                from babylon60.audit.smt import SparseMerkleTree

                smt_state = SparseMerkleTree()
            for aid in batch_audit_ids:
                smt_state.update(cortex_hash(aid.encode()), aid)
            merkle_root = smt_state.root
            entry_hash = cortex_hash(f"merkle_batch:{merkle_root}:{prev_hash}".encode())

            self.public_key.verify(bytes.fromhex(signature_hex), entry_hash.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False

    async def compact_ledger(
        self, max_rows: int = 10000, snapshot_dir: Path | None = None
    ) -> dict[str, Any]:
        """[C5-REAL] Compacts historical ledger events into a cryptographic snapshot.
        Delegates to ledger_compactor to preserve the SMT hash chain via COMPACTION_NODE.
        """
        from babylon60.audit.ledger_compactor import compact_ledger as run_compaction

        return await run_compaction(self._conn, self, max_rows, snapshot_dir)
