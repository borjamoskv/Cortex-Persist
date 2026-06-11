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
    signature TEXT NOT NULL
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

        # C5-REAL Sovereign Ed25519 Keypair (Audit ZK-Seal Substrate)
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_sovereign.pem")
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                pk = serialization.load_pem_private_key(key_file.read(), password=None)
            assert isinstance(pk, ed25519.Ed25519PrivateKey)
            self.private_key = pk
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            with open(key_path, "wb") as key_file:
                key_file.write(
                    self.private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
        self.public_key = self.private_key.public_key()

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            async with AsyncFileLock():
                if self._ready:
                    return
                await self._conn.execute(_CREATE_AUDIT_SQL)
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

    async def run_scan(self) -> dict[str, Any]:
        return {"status": "scan_not_implemented"}

    async def _batch_worker(self) -> None:
        """Background worker that flushes the queue periodically using a Merkle Tree."""
        import asyncio

        while True:
            await asyncio.sleep(self.batch_window_ms / 1000.0)
            async with self._lock:
                async with AsyncFileLock():
                    if not self._batch_queue:
                        self._batch_task = None
                        break

                    batch = self._batch_queue[: self.max_batch_size]
                    self._batch_queue = self._batch_queue[self.max_batch_size :]

                    # Compute Merkle Root for the batch
                    batch_audit_ids = [item["audit_id"] for item, _ in batch]
                    merkle_payload = "".join(batch_audit_ids) + self._last_hash
                    merkle_root = hashlib.sha256(merkle_payload.encode()).hexdigest()

                    # Separate hash from signature: entry_hash represents the batch deterministically
                    entry_hash_payload = f"merkle_batch:{merkle_root}:{self._last_hash}"
                    entry_hash = hashlib.sha256(entry_hash_payload.encode()).hexdigest()

                    # Sign the entry_hash
                    signature = self.private_key.sign(entry_hash.encode()).hex()

                    # Prepare SQLite bulk insert
                    insert_rows = []
                    for item, _ in batch:
                        insert_rows.append(
                            (
                                item["audit_id"],
                                item["timestamp"],
                                item["tenant_id"],
                                item["actor_role"],
                                item["actor_id"],
                                item["action"],
                                item["resource"],
                                item["status"],
                                self._last_hash,
                                signature,
                            )
                        )

                    try:
                        await self._conn.executemany(
                            """INSERT INTO security_audit_log
                               (audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                                resource, status, prev_hash, signature)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            insert_rows,
                        )
                        await self._conn.commit()
                        self._last_hash = entry_hash

                        # Resolve futures
                        for item, fut in batch:
                            if not fut.done():
                                fut.set_result(item["audit_id"])
                    except (OSError, ValueError, RuntimeError) as e:
                        logger.error("[AuditLedger] Batch insert failed: %s", e)
                        for _, fut in batch:
                            if not fut.done():
                                fut.set_exception(e)

    async def log_action(
        self,
        tenant_id: str,
        actor_role: str,
        actor_id: str,
        action: str,
        resource: str,
        status: str = "SUCCESS",
    ) -> str:
        """Securely logs an action. Uses Micro-Batching under concurrency."""
        import asyncio

        await self.ensure_table()

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        audit_id = hashlib.sha256(f"{timestamp}{actor_id}{action}".encode()).hexdigest()

        event = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "tenant_id": tenant_id,
            "actor_role": actor_role,
            "actor_id": actor_id,
            "action": action,
            "resource": resource,
            "status": status,
        }

        fut = asyncio.get_running_loop().create_future()

        async with self._lock:
            self._batch_queue.append((event, fut))
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._batch_worker())

        # Wait for the batch to be committed
        return await fut

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
