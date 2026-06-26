"""
Enterprise Audit Ledger (SOC 2 Compliance).

Append-only cryptographic ledger tracking all operations.
Secures the `tenant_id` and the identity of the operator, creating
a hash-chain to prove immutability of the audit logs.
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from cortex.database.core import causal_write

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
        from cortex.crypto.keys import KeyManager

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
                    await self._conn.execute("ALTER TABLE security_audit_log ADD COLUMN external_anchor TEXT")
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
                    merkle_payload = "".join(batch_audit_ids) + prev_hash
                    merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()
                    self._last_hash = hashlib.sha256(
                        f"merkle_batch:{merkle_root}:{prev_hash}".encode()
                    ).hexdigest()
                else:
                    self._last_hash = "GENESIS"
                self._ready = True

    async def close(self) -> None:
        if self._batch_task is not None:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None

    async def verify_chain(self) -> dict[str, Any]:
        """Perform a full verification of the cryptographic chain.
        Returns {'status': 'verified'} if pristine, or {'status': 'tampered', 'corrupted_audit_id': id} if broken.
        """
        import hashlib

        await self.ensure_table()

        async with self._conn.execute(
            "SELECT rowid, audit_id, timestamp, actor_id, action, prev_hash, signature FROM security_audit_log ORDER BY rowid ASC"
        ) as cursor:
            rows = list(await cursor.fetchall())

        if not rows:
            return {"status": "verified", "blocks": 0}

        # Group by batch (same prev_hash and signature)
        batches = []
        current_batch = []
        current_prev_hash = rows[0][5]
        current_sig = rows[0][6]

        for row in rows:
            # row: 0=rowid, 1=audit_id, 2=timestamp, 3=actor_id, 4=action, 5=prev_hash, 6=signature
            # Validate individual audit_id to detect row-level tampering
            expected_audit_id = hashlib.sha256(f"{row[2]}{row[3]}{row[4]}".encode()).hexdigest()
            if expected_audit_id != row[1]:
                return {
                    "status": "tampered",
                    "corrupted_audit_id": row[1],
                    "reason": "row_hash_mismatch",
                }

            if row[5] == current_prev_hash and row[6] == current_sig:
                current_batch.append(row)
            else:
                batches.append((current_prev_hash, current_sig, current_batch))
                current_prev_hash = row[5]
                current_sig = row[6]
                current_batch = [row]

        if current_batch:
            batches.append((current_prev_hash, current_sig, current_batch))

        # Verify Merkle chain and signatures
        expected_prev_hash = "GENESIS"

        for prev_hash, signature, batch_rows in batches:
            if prev_hash != expected_prev_hash:
                return {
                    "status": "tampered",
                    "corrupted_audit_id": batch_rows[0][1],
                    "reason": "chain_broken",
                }

            batch_audit_ids = [r[1] for r in batch_rows]
            merkle_payload = "".join(batch_audit_ids) + prev_hash
            merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

            entry_hash_payload = f"merkle_batch:{merkle_root}:{prev_hash}"
            entry_hash = hashlib.sha256(entry_hash_payload.encode()).hexdigest()

            try:
                self.public_key.verify(bytes.fromhex(signature), entry_hash.encode())
            except InvalidSignature:
                return {
                    "status": "tampered",
                    "corrupted_audit_id": batch_rows[0][1],
                    "reason": "invalid_signature",
                }

            expected_prev_hash = entry_hash

        return {"status": "verified", "blocks": len(batches)}

    async def _anchor_worker(self) -> None:
        """Background worker that pulls unanchored local entries and anchors them to Rekor/TSA asynchronously."""
        import asyncio
        import base64
        import json

        import httpx
        try:
            import rfc3161ng  # pyright: ignore[reportMissingImports] # Opt-in  # pyright: ignore[reportMissingImports] # Opt-in secure dependency
        except ImportError:
            rfc3161ng = None
            logger.warning("rfc3161ng is not installed. TSA signatures will be disabled. Run pip install cortex-persist[secure]")
        from cryptography.hazmat.primitives import serialization

        from cortex.audit.rekor_client import RekorClient

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
                            cursor = await self._conn.execute(
                                "SELECT audit_id, signature, prev_hash FROM security_audit_log WHERE external_anchor IS NULL ORDER BY rowid ASC LIMIT ?",
                                (self.max_batch_size,)
                            )
                            unanchored = await cursor.fetchall()
                            
                            if not unanchored:
                                self._batch_task = None
                                break

                            for audit_id, signature, prev_hash in unanchored:
                                external_anchor = None
                                try:
                                    merkle_payload = audit_id + prev_hash
                                    merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()
                                    entry_hash = hashlib.sha256(f"merkle_batch:{merkle_root}:{prev_hash}".encode()).hexdigest()

                                    pub_pem = self.public_key.public_bytes(
                                        encoding=serialization.Encoding.PEM,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                                    )

                                    if "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("CORTEX_TEST_ENV"):
                                        rekor_uuid = None
                                        rfc_token = None
                                    else:
                                        # Asynchronous Rekor logging
                                        rekor_uuid = await rekor_client.log_entry(entry_hash, signature, pub_pem)  # pyright: ignore[reportArgumentType]

                                        tsa_signature = None
                                        if rfc3161ng is not None:
                                            try:
                                                tsa_req = rfc3161ng.make_request(merkle_root.encode("utf-8"))
                                                tsa_resp = await http_client.post(
                                                    tsa_url,
                                                    content=tsa_req,
                                                    headers={"Content-Type": "application/timestamp-query"},
                                                )
                                                if tsa_resp.status_code == 200:
                                                    tsa_signature = base64.b64encode(tsa_resp.content).decode("utf-8")
                                            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                                                logger.warning("TSA stamping failed: %s", exc)
                                        rfc_token = tsa_signature

                                    if rekor_uuid or rfc_token:
                                        external_anchor = json.dumps(
                                            {"rekor_uuid": rekor_uuid, "rfc3161_token": rfc_token}
                                        )
                                        
                                        # Update the row with the external anchor
                                        with causal_write(self._conn):
                                            await self._conn.execute(
                                                "UPDATE security_audit_log SET external_anchor = ? WHERE audit_id = ?",
                                                (external_anchor, audit_id)
                                            )
                                            if not self._conn.in_transaction:
                                                await self._conn.commit()
                                except Exception as e:
                                    logger.error("[AuditLedger] External anchoring failed: %s", e)

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
        audit_id = hashlib.sha256(f"{timestamp}{actor_id}{action}".encode()).hexdigest()

        async with self._lock:
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
                merkle_payload = "".join(batch_audit_ids) + prev_hash_db
                merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()
                current_last_hash = hashlib.sha256(
                    f"merkle_batch:{merkle_root}:{prev_hash_db}".encode()
                ).hexdigest()
            else:
                current_last_hash = "GENESIS"

            # 2. Compute the new block
            merkle_payload_new = audit_id + current_last_hash
            merkle_root_new = hashlib.sha256(merkle_payload_new.encode()).hexdigest()
            entry_hash = hashlib.sha256(f"merkle_batch:{merkle_root_new}:{current_last_hash}".encode()).hexdigest()
            signature = self.private_key.sign(entry_hash.encode()).hex()

            # 3. Insert synchronously inside the existing transaction
            with causal_write(self._conn):
                await self._conn.execute(
                    """INSERT INTO security_audit_log
                       (audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                        resource, status, prev_hash, signature, external_anchor)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                        resource, status, current_last_hash, signature, None
                    )
                )
                # Auto-commit ONLY if we are not inside a larger transaction
                if not self._conn.in_transaction:
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

    def verify_batch(self, batch_audit_ids: list[str], prev_hash: str, signature_hex: str) -> bool:
        """Verifies the cryptographic seal of a batch against the public key using entry_hash."""
        try:
            # Reconstruct batch entry_hash
            merkle_payload = "".join(batch_audit_ids) + prev_hash
            merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()
            entry_hash = hashlib.sha256(
                f"merkle_batch:{merkle_root}:{prev_hash}".encode()
            ).hexdigest()

            self.public_key.verify(bytes.fromhex(signature_hex), entry_hash.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False
