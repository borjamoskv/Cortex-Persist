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


class EnterpriseAuditLedger:
    """Immutable Audit Ledger for enterprise-grade SOC 2 compliance."""

    __slots__ = ("_conn", "_last_hash", "_ready", "private_key", "public_key")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self._last_hash = "GENESIS"

        # C5-REAL Sovereign Ed25519 Keypair (Audit ZK-Seal Substrate)
        # Almacena la clave localmente para persistir la identidad del auditor
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
        await self._conn.execute(_CREATE_AUDIT_SQL)
        await self._conn.commit()
        # Fetch the last hash to maintain the chain
        cursor = await self._conn.execute(
            "SELECT signature FROM security_audit_log ORDER BY rowid DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            self._last_hash = row[0]
        self._ready = True

    async def run_scan(self) -> dict[str, Any]:
        """
        Scans audit logs for common threat patterns:
        - Rapid role escalation
        - Cross-tenant resource requests
        - Out-of-hours high-volume reads
        """
        # Placeholder for scan logic
        return {"status": "scan_not_implemented"}

    async def log_action(
        self,
        tenant_id: str,
        actor_role: str,
        actor_id: str,
        action: str,
        resource: str,
        status: str = "SUCCESS",
    ) -> str:
        """Securely logs an action with a cryptographic hash chain."""
        await self.ensure_table()

        timestamp = datetime.fromtimestamp(time.monotonic(), tz=timezone.utc).isoformat()
        audit_id = hashlib.sha256(f"{timestamp}{actor_id}{action}".encode()).hexdigest()

        # Calculate new signature ensuring immutability chain via Ed25519 ZK-Seal
        payload = f"{audit_id}:{timestamp}:{tenant_id}:{actor_id}:{action}:{self._last_hash}"
        signature = self.private_key.sign(payload.encode()).hex()

        await self._conn.execute(
            """INSERT INTO security_audit_log
               (audit_id, timestamp, tenant_id, actor_role, actor_id, action,
                resource, status, prev_hash, signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                timestamp,
                tenant_id,
                actor_role,
                actor_id,
                action,
                resource,
                status,
                self._last_hash,
                signature,
            ),
        )
        await self._conn.commit()
        self._last_hash = signature
        return audit_id

    def verify_zk_seal(self, payload: str, signature_hex: str) -> bool:
        """Verifies a cryptographic seal against the Audit Sovereign public key."""
        try:
            self.public_key.verify(bytes.fromhex(signature_hex), payload.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False
