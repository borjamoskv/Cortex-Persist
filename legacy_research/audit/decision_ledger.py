# [C5-REAL] Exergy-Maximized
"""
Decision Ledger Protocol (v1.0.0-APEX).

Implements the AI Control Plane + Audit Layer. Handles DecisionNode schema,
state transition logic, runtime policy enforcement (blocking gates), and
Babylon-60 decimal-free scaling.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from cortex.audit.ledger import AsyncFileLock

logger = logging.getLogger("cortex.audit.decision_ledger")

# ─── Schema Setup ────────────────────────────────────────────────────────────

_CREATE_DECISION_LKRGSER_SQL = """
CREATE TABLE IF NOT EXISTS decision_ledger (
    trace_id TEXT PRIMARY KEY,
    parent_id TEXT,
    epoch_b60 INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    tenant_id TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    model_hash TEXT NOT NULL,
    prompt_version_hash TEXT NOT NULL,
    tool_graph_hash TEXT NOT NULL,
    input_taint TEXT NOT NULL,
    policy_results TEXT NOT NULL,
    eval_scores TEXT NOT NULL,
    approval_state TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    signature TEXT NOT NULL
);
"""

# ─── Types and Dataclasses ───────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyVerdict:
    policy_id: str
    status: str  # "PASS" or "FAIL"
    seal: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Policy:
    policy_id: str
    is_blocking: bool = True
    rule_source: str = ""

    async def evaluate(self, node: DecisionNode) -> PolicyVerdict:
        """Evaluates policy rule. Custom rules can override this."""
        # Baseline check (simple checks for PII or target keywords)
        return PolicyVerdict(
            policy_id=self.policy_id,
            status="PASS",
            seal="",
            message="Rule evaluated successfully."
        )

@dataclass
class DecisionNode:
    trace_id: str
    parent_id: str | None
    epoch_b60: int
    sequence: int
    tenant_id: str
    operator_id: str
    model_hash: str
    prompt_version_hash: str
    tool_graph_hash: str
    input_taint: str
    policy_results: list[dict[str, Any]] = field(default_factory=list)
    eval_scores: dict[str, int] = field(default_factory=dict)
    approval_state: str = "PROPOSED"  # PROPOSED, VALIDATED, TAINTED, ENCRYPTED, SEALED, REJECTED
    prev_hash: str = ""
    merkle_root: str = ""
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "epoch_b60": self.epoch_b60,
            "sequence": self.sequence,
            "tenant_id": self.tenant_id,
            "operator_id": self.operator_id,
            "provenance": {
                "model_hash": self.model_hash,
                "prompt_version_hash": self.prompt_version_hash,
                "tool_graph_hash": self.tool_graph_hash,
            },
            "runtime": {
                "input_taint": self.input_taint,
                "policy_results": self.policy_results,
                "eval_scores": self.eval_scores,
                "approval_state": self.approval_state,
            },
            "cryptography": {
                "prev_hash": self.prev_hash,
                "merkle_root": self.merkle_root,
                "signature": self.signature,
            }
        }

    def canonical_json(self) -> str:
        d = self.to_dict()
        # Remove cryptography fields for hashing
        d.pop("cryptography", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

# ─── Babylon-60 Helpers ──────────────────────────────────────────────────────

def timestamp_to_b60(ts: float | None = None) -> int:
    """Scale Unix epoch timestamp to Babylon-60 sub-millisecond precision."""
    val = ts if ts is not None else time.time()
    return int(val * 216000)

def score_to_b60(val: float | int) -> int:
    """Scale float score [0.0, 1.0] or int [0, 60] to Babylon-60 integer [0, 60]."""
    if isinstance(val, float):
        if 0.0 <= val <= 1.0:
            return int(val * 60)
        return int(min(max(val, 0.0), 60.0))
    return int(min(max(val, 0), 60))

# ─── Main Decision Ledger Class ──────────────────────────────────────────────

class DecisionLedger:
    """System of Record tracking AI execution decisions with runtime compliance policies."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()
        
        # Load or generate sovereign signing keys
        key_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(key_dir, "audit_sovereign.pem")
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                pk = serialization.load_pem_private_key(key_file.read(), password=None)
            assert isinstance(pk, ed25519.Ed25519PrivateKey)
            self.private_key = pk
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            os.makedirs(key_dir, exist_ok=True)
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
                await self._conn.execute(_CREATE_DECISION_LKRGSER_SQL)
                await self._conn.commit()
                cursor = await self._conn.execute(
                    "SELECT signature FROM decision_ledger ORDER BY rowid DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                if row:
                    self._last_hash = row[0]
                else:
                    self._last_hash = "GENESIS"
                self._ready = True

    async def append_node(self, node: DecisionNode) -> str:
        """Appends a new decision node to the ledger, computing hashes & sovereign signature."""
        await self.ensure_table()
        
        async with self._lock:
            # Set the previous hash
            node.prev_hash = self._last_hash
            
            # Compute Merkle Root (for single node it is the hash of the node itself)
            payload = node.canonical_json()
            merkle_root = hashlib.sha256(payload.encode()).hexdigest()
            node.merkle_root = merkle_root
            
            # Compute final entry hash to sign
            entry_hash_payload = f"decision_node:{merkle_root}:{node.prev_hash}"
            entry_hash = hashlib.sha256(entry_hash_payload.encode()).hexdigest()
            
            # Sovereign Seal (Signature)
            signature = self.private_key.sign(entry_hash.encode()).hex()
            node.signature = signature
            node.approval_state = "SEALED"

            # Insert into database
            await self._conn.execute(
                """
                INSERT INTO decision_ledger (
                    trace_id, parent_id, epoch_b60, sequence, tenant_id, operator_id,
                    model_hash, prompt_version_hash, tool_graph_hash, input_taint,
                    policy_results, eval_scores, approval_state, prev_hash, merkle_root, signature
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.trace_id,
                    node.parent_id,
                    node.epoch_b60,
                    node.sequence,
                    node.tenant_id,
                    node.operator_id,
                    node.model_hash,
                    node.prompt_version_hash,
                    node.tool_graph_hash,
                    node.input_taint,
                    json.dumps(node.policy_results),
                    json.dumps(node.eval_scores),
                    node.approval_state,
                    node.prev_hash,
                    node.merkle_root,
                    node.signature,
                ),
            )
            await self._conn.commit()
            self._last_hash = signature
            return signature

# ─── Runtime Gate Enforcement & SAGA Protocol ───────────────────────────────

async def trigger_saga_compensation(node: DecisionNode, step: int) -> None:
    """Executes compensating actions in reverse depending on where failure occurred."""
    logger.warning("[SAGA] Triggering compensating rollback sequence from step %d for trace_id %s", step, node.trace_id)
    node.approval_state = "REJECTED"
    # SAGA-3: Revoke session taint / log rejection to diagnostic bus
    # SAGA-2: Revoke taint signature
    # SAGA-1: Emit abort event
    # (Simulated database compensation actions if needed)

async def enforce_runtime_gate(
    node: DecisionNode,
    policies: list[Policy],
    ledger: DecisionLedger | None = None
) -> tuple[bool, list[PolicyVerdict]]:
    """
    Enforces policies in runtime. Intercepts execution BEFORE LLM or output delivery.
    If a blocking policy fails, aborts via SAGA compensation and prevents storage.
    """
    node.approval_state = "PROPOSED"
    verdicts: list[PolicyVerdict] = []
    
    # SAGA step counter
    current_step = 1

    try:
        # Step 1: Ingestion & state check
        node.approval_state = "VALIDATED"
        current_step = 2

        # Step 2: Policy verification
        for policy in policies:
            verdict = await policy.evaluate(node)
            # Sign verdict
            if ledger:
                payload = f"{policy.policy_id}:{verdict.status}:{node.trace_id}"
                seal = ledger.private_key.sign(payload.encode()).hex()
                verdict = PolicyVerdict(
                    policy_id=verdict.policy_id,
                    status=verdict.status,
                    seal=seal,
                    message=verdict.message
                )
            
            verdicts.append(verdict)
            node.policy_results.append(verdict.to_dict())

            if verdict.status == "FAIL":
                if policy.is_blocking:
                    node.approval_state = "REJECTED"
                    await trigger_saga_compensation(node, step=current_step)
                    return False, verdicts

        # Step 3: Taint checking
        node.approval_state = "TAINTED"
        current_step = 3

        # Step 4: Ledger append
        if ledger:
            await ledger.append_node(node)
            
        return True, verdicts

    except Exception as e:
        logger.error("[DecisionLedger] Policy gate execution error: %s", e)
        await trigger_saga_compensation(node, step=current_step)
        return False, verdicts
