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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

import cortex_core_rs
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

    def __init__(self, log_path: str = "security_audit_log.jsonl") -> None:
        self.log_path = log_path
        self._lock = asyncio.Lock()
        self._batch_queue: list[dict] = []
        self._batch_task: asyncio.Task | None = None

        # Configure thresholds
        self.batch_window_ms = int(os.environ.get("CORTEX_LKRGSER_BATCH_MS", "50"))
        self.max_batch_size = int(os.environ.get("CORTEX_LKRGSER_MAX_BATCH", "128"))
        self._last_hash = "GENESIS"

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

                # Use Rust bindings to compute the Merkle root
                batch_hashes = [evt["event_hash"] for evt in batch]
                merkle_root = cortex_core_rs.batch_merkle_root(batch_hashes)
                
                # Sign the Merkle root
                signature = self.private_key.sign(merkle_root.encode("utf-8")).hex()

                batch_event = {
                    "type": "BATCH_ROOT",
                    "batch_root": merkle_root,
                    "prev_hash": self._last_hash,
                    "signature": signature,
                    "size": len(batch)
                }

                # Write to JSONL WORM
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
        trace_id: str = None,
        parent_span_id: str = None,
        is_code: bool = False
    ) -> str:
        """Securely logs an action. Generates triple identity and canonical hash."""
        ident = generate_event_identity(trace_id=trace_id, parent_span_id=parent_span_id)
        
        ast_hash = None
        if is_code and state_diff:
            try:
                parsed_ast = ast.parse(state_diff)
                canonical_ast = ast.dump(parsed_ast)
                ast_hash = hashlib.sha3_256(canonical_ast.encode('utf-8')).hexdigest()
            except SyntaxError:
                ast_hash = "INVALID_SYNTAX"

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
        previous_fitness: float,
        trace_id: str = None
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
        batch_size: int,
        trace_id: str = None
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

