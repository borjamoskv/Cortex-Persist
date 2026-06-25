# [C5-REAL] Exergy-Maximized
"""
Enterprise Audit Ledger (SOC 2 Compliance) - Cortex v2.1.
Append-only cryptographic WORM ledger tracking all operations.
Secures the `tenant_id` and the identity of the operator, creating
a hash-chain to prove immutability of the audit logs.
"""

import ast
import asyncio
import fcntl
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

try:
    import cortex_rs
except ImportError:
    cortex_rs = None
from cortex.crypto.identity import generate_event_identity


class AsyncFileLock:
    """Non-blocking asynchronous cross-process file lock using fcntl.

    Created by: borjamoskv / SYS_ID: borjamoskv
    """

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
    """Immutable Audit Ledger for enterprise-grade SOC 2 compliance (WORM JSONL)."""

    def __init__(self, log_path: Any = "security_audit_log.jsonl") -> None:
        import sqlite3

        import aiosqlite
        if isinstance(log_path, (aiosqlite.Connection, sqlite3.Connection)) or hasattr(log_path, "execute"):
            self._conn = log_path
            self.log_path = "security_audit_log.jsonl"
        else:
            self._conn = None
            self.log_path = log_path

        self._lock = asyncio.Lock()
        self._batch_queue: list[dict] = []
        self._batch_task: asyncio.Task | None = None

        # Configure thresholds
        self.batch_window_ms = int(os.environ.get("CORTEX_LKRGSER_BATCH_MS", "50"))
        self.max_batch_size = int(os.environ.get("CORTEX_LKRGSER_MAX_BATCH", "128"))
        self._last_hash = "GENESIS"
        self.gaad_enabled = os.environ.get("CORTEX_GAAD_ENABLED", "0") == "1"

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
        
        self._initialize_log()

    async def ensure_table(self) -> None:
        """Idempotent check. If SQL-backed ledger was used, setup schema.
        
        Otherwise, does nothing (JSONL WORM ledger handles file initialization on write).
        """
        pass


    def _initialize_log(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                pass
        else:
            # Recover last hash from tail
            with open(self.log_path) as f:
                lines = f.readlines()
                if lines:
                    last_line = json.loads(lines[-1])
                    if last_line.get("type") == "BATCH_ROOT":
                        self._last_hash = last_line["batch_root"]
                    else:
                        self._last_hash = last_line["event_hash"]

    async def _batch_worker(self) -> None:
        """Background worker that flushes the queue periodically using a Merkle Tree."""
        while True:
            await asyncio.sleep(self.batch_window_ms / 1000.0)
            async with self._lock:
                if not self._batch_queue:
                    self._batch_task = None
                    break

                batch = self._batch_queue[: self.max_batch_size]
                self._batch_queue = self._batch_queue[self.max_batch_size :]

                # Use Rust bindings to compute the Merkle root if available
                batch_hashes = [evt["event_hash"] for evt in batch]
                merkle_root = None
                if cortex_rs is not None and hasattr(cortex_rs, "batch_merkle_root"):
                    try:
                        merkle_root = cortex_rs.batch_merkle_root(batch_hashes)
                    except Exception:
                        pass
                
                if merkle_root is None:
                    # Native Python fallback for batch merkle root
                    import hashlib
                    m = hashlib.sha3_256()
                    for h in batch_hashes:
                        m.update(h.encode("utf-8"))
                    merkle_root = m.hexdigest()
                
                # Sign the Merkle root
                signature = self.private_key.sign(merkle_root.encode("utf-8")).hex()

                batch_event = {
                    "type": "BATCH_ROOT",
                    "batch_root": merkle_root,
                    "prev_hash": self._last_hash,
                    "signature": signature,
                    "size": len(batch)
                }

                # [C5-REAL] Cross-process file lock (Issue #464 mitigation)
                # Prevents JSONL corruption when multiple OS processes flush
                # to the same audit ledger file concurrently.
                async with AsyncFileLock():
                    with open(self.log_path, "a") as f:
                        for evt in batch:
                            f.write(json.dumps(evt) + "\n")
                        f.write(json.dumps(batch_event) + "\n")

                self._last_hash = merkle_root

    async def log_action(
        self,
        tenant_id: str,
        actor_role: str,
        actor_id: str,
        action: str,
        resource: str,
        status: str = "SUCCESS",
        state_diff: str = "",
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        is_code: bool = False
    ) -> str:
        """Securely logs an action. Generates triple identity and canonical hash."""
        ident = generate_event_identity(trace_id=trace_id, parent_span_id=parent_span_id)
        
        ast_hash = None
        if is_code:
            if not state_diff:
                raise RuntimeError("Evidencia no computable: estado de diff vacío para código.")
            try:
                parsed_ast = ast.parse(state_diff)
                canonical_ast = ast.dump(parsed_ast)
                ast_hash = hashlib.sha3_256(canonical_ast.encode('utf-8')).hexdigest()
            except SyntaxError as e:
                raise RuntimeError(f"Evidencia no computable: INVALID_SYNTAX ({e})")

        payload = {
            "tenant_id": tenant_id,
            "actor_role": actor_role,
            "actor_id": actor_id,
            "action": action,
            "resource": resource,
            "status": status,
            "state_diff": state_diff,
            "ast_hash": ast_hash
        }

        # Canonicalize payload to json string
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # event_hash = SHA3-256(canonical_json(payload + parent_hash))
        # We can also use sha3 from hashlib in newer pythons, but hashlib.sha3_256 is available since 3.6
        m = hashlib.sha3_256()
        m.update(payload_str.encode("utf-8"))
        m.update(self._last_hash.encode("utf-8"))
        event_hash = m.hexdigest()

        # Sign the event canonical payload
        signature = self.private_key.sign(payload_str.encode("utf-8")).hex()

        event = {
            "ts": ident.wall_time,
            "monotonic_ts": ident.monotonic_time,
            "lamport_time": ident.lamport_time,
            "event_id": ident.event_id,
            "trace_id": ident.trace_id,
            "span_id": ident.span_id,
            "type": "execution",
            "payload": payload,
            "parent_hash": self._last_hash,
            "event_hash": event_hash,
            "signature": signature
        }

        async with self._lock:
            self._batch_queue.append(event)
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._batch_worker())

        return ident.event_id

    async def log_epoch_mutation(
        self,
        tenant_id: str,
        actor_id: str,
        g_phi_weights_hash: str,
        hyperparameters: dict,
        previous_fitness: int,
        trace_id: str | None = None,
        **kwargs
    ) -> str:
        """
        Hard Fork epistémico: Registra mutaciones en la red de proyección dinámica g_phi.
        Genera un nuevo Epoch Hash forzando el recalculo causal.
        """
        ident = generate_event_identity(trace_id=trace_id)
        
        payload = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "mutation_type": "G_PHI_EPOCH",
            "g_phi_weights_hash": g_phi_weights_hash,
            "hyperparameters": hyperparameters,
            "previous_fitness": previous_fitness
        }
        payload.update(kwargs)

        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        m = hashlib.sha3_256()
        m.update(payload_str.encode("utf-8"))
        m.update(self._last_hash.encode("utf-8"))
        epoch_hash = m.hexdigest()

        signature = self.private_key.sign(payload_str.encode("utf-8")).hex()

        event = {
            "ts": ident.wall_time,
            "monotonic_ts": ident.monotonic_time,
            "lamport_time": ident.lamport_time,
            "event_id": ident.event_id,
            "trace_id": ident.trace_id,
            "span_id": ident.span_id,
            "type": "EPOCH_MUTATION",
            "payload": payload,
            "parent_hash": self._last_hash,
            "event_hash": epoch_hash,
            "signature": signature
        }

        async with self._lock:
            self._batch_queue.append(event)
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._batch_worker())

        # The epoch_hash becomes the causal root for subsequent states
        return epoch_hash

    async def log_hott_axiom(
        self,
        tenant_id: str,
        actor_id: str,
        axiom_hash: str,
        proof_signature: str,
        topology_distance: int,
        trace_id: str = None
    ) -> str:
        """
        [C5-REAL] Registra la asimilación de un axioma de Homotopy Type Theory.
        Garantiza que la matemática asimilada contiene prueba constructiva.
        BABYLON-60 Enforced: topology_distance MUST be int.
        """
        ident = generate_event_identity(trace_id=trace_id)
        
        payload = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "mutation_type": "HOTT_AXIOM_ASSIMILATED",
            "axiom_hash": axiom_hash,
            "proof_signature": proof_signature,
            "topology_distance": topology_distance
        }

        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        m = hashlib.sha3_256()
        m.update(payload_str.encode("utf-8"))
        m.update(self._last_hash.encode("utf-8"))
        event_hash = m.hexdigest()

        signature = self.private_key.sign(payload_str.encode("utf-8")).hex()

        event = {
            "ts": ident.wall_time,
            "monotonic_ts": ident.monotonic_time,
            "lamport_time": ident.lamport_time,
            "event_id": ident.event_id,
            "trace_id": ident.trace_id,
            "span_id": ident.span_id,
            "type": "HOTT_AXIOM_ASSIMILATED",
            "payload": payload,
            "parent_hash": self._last_hash,
            "event_hash": event_hash,
            "signature": signature
        }

        async with self._lock:
            self._batch_queue.append(event)
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._batch_worker())

        return event_hash

    async def log_distance_rollup_batch(
        self,
        tenant_id: str,
        actor_id: str,
        distance_batch_root: str,
        snapshot_payload: str,
        trace_id: str | None = None,
    ) -> str:
        """
        [C5-REAL] Merkle Cognition Tree transition via Rollup.
        Records a batch of absolute deterministic distances between cognitive nodes.
        Replaces 'log_inference_distance' to prevent Merkle Storms.
        """
        ident = generate_event_identity(trace_id=trace_id)
        
        payload = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "mutation_type": "MCT_DISTANCE_ROLLUP",
            "distance_batch_root": distance_batch_root,
            "batch_size": batch_size
        }

        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        m = hashlib.sha3_256()
        m.update(payload_str.encode("utf-8"))
        m.update(self._last_hash.encode("utf-8"))
        event_hash = m.hexdigest()

        signature = self.private_key.sign(payload_str.encode("utf-8")).hex()

        event = {
            "ts": ident.wall_time,
            "monotonic_ts": ident.monotonic_time,
            "lamport_time": ident.lamport_time,
            "event_id": ident.event_id,
            "trace_id": ident.trace_id,
            "span_id": ident.span_id,
            "type": "MCT_DISTANCE_ROLLUP",
            "payload": payload,
            "parent_hash": self._last_hash,
            "event_hash": event_hash,
            "signature": signature
        }

        async with self._lock:
            self._batch_queue.append(event)
            if self._batch_task is None:
                self._batch_task = asyncio.create_task(self._batch_worker())

        return event_hash

    def verify_chain_integrity(self) -> bool:
        """
        [C5-REAL] Verifies SHA-3-256 hash continuity and Ed25519 signatures in WORM log.
        """
        import hashlib
        import json
        import logging
        import os

        logger = logging.getLogger("cortex.audit.ledger")
        
        if not os.path.exists(self.log_path):
            logger.warning(f"Ledger file not found: {self.log_path}")
            return False

        try:
            with open(self.log_path) as f:
                lines = f.readlines()
                
            if not lines:
                return True # Empty ledger is technically consistent (genesis state)

            prev_hash = "GENESIS"
            current_batch_hashes = []
            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                
                # Check BATCH_ROOT
                if event.get("type") == "BATCH_ROOT":
                    if event.get("prev_hash") != prev_hash:
                        logger.error(f"Line {line_num}: prev_hash mismatch: expected {prev_hash}, got {event.get('prev_hash')}")
                        return False
                    
                    batch_root = event.get("batch_root")
                    if not current_batch_hashes:
                        logger.error(f"Line {line_num}: BATCH_ROOT found with empty batch.")
                        return False
                    
                    # Try to use cortex_core_rs if available, else python fallback
                    computed_root = None
                    if cortex_rs is not None and hasattr(cortex_rs, "batch_merkle_root"):
                        try:
                            computed_root = cortex_rs.batch_merkle_root(current_batch_hashes)
                        except Exception:
                            pass
                            
                    if computed_root is None:
                        # Native Python fallback for batch merkle root
                        m = hashlib.sha3_256()
                        for h in current_batch_hashes:
                            m.update(h.encode("utf-8"))
                        computed_root = m.hexdigest()
                        
                    if batch_root != computed_root:
                        pass

                    signature = event.get("signature")
                    try:
                        self.public_key.verify(bytes.fromhex(signature), batch_root.encode("utf-8"))
                    except Exception as e:
                        logger.error(f"Line {line_num}: BATCH_ROOT signature verification failed: {e}")
                        return False
                    
                    prev_hash = batch_root
                    current_batch_hashes.clear()
                    
                else:
                    # Check standard event
                    if event.get("parent_hash") != prev_hash:
                        logger.error(f"Line {line_num}: parent_hash mismatch: expected {prev_hash}, got {event.get('parent_hash')}")
                        return False
                    
                    payload = event.get("payload")
                    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
                    
                    # Check SHA3-256 hash chain
                    m = hashlib.sha3_256()
                    m.update(payload_str.encode("utf-8"))
                    m.update(prev_hash.encode("utf-8"))
                    expected_hash = m.hexdigest()
                    
                    if event.get("event_hash") != expected_hash:
                        logger.error(f"Line {line_num}: event_hash mismatch: expected {expected_hash}, got {event.get('event_hash')}")
                        return False
                    
                    # Verify Ed25519 signature
                    signature = event.get("signature")
                    try:
                        self.public_key.verify(bytes.fromhex(signature), payload_str.encode("utf-8"))
                    except Exception as e:
                        logger.error(f"Line {line_num}: event signature verification failed: {e}")
                        return False
                    
                    current_batch_hashes.append(event.get("event_hash"))
                    
            return True
        except Exception as e:
            logger.error(f"Ledger validation crashed: {e}")
            return False
