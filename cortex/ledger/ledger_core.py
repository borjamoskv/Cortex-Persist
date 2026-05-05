"""
CORTEX v8 — Sovereign Immutable Ledger (CHRONOS-1 Standard).

Axiom Reference:
- Ω₃ (Byzantine Default): "I verify, then trust. Never reversed."
- Ω₂ (Entropic Asymmetry): "Merkle Trees reduce trust-cost from O(N) to O(log N)."
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex.utils.canonical import (
    canonical_json,
    compute_tx_hash,
    compute_tx_hash_v1,
    now_iso,
)

logger = logging.getLogger("cortex.ledger")


@dataclass(frozen=True)
class MerkleNode:
    """A node within the Merkle Tree (V8 Immutable)."""

    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False


class MerkleTree:
    """High-performance Merkle Tree for batch transaction verification."""

    def __init__(self, leaves: list[str]):
        if not leaves:
            self.root = None
            self._leaves = []
            return

        self._leaves = leaves
        nodes = [MerkleNode(hash=h, is_leaf=True) for h in leaves]
        self.layers = []
        self.root = self._build_recursive(nodes)

    def _hash_pair(self, left: str, right: str) -> str:
        return hashlib.sha256((left + right).encode()).hexdigest()

    def _build_recursive(self, nodes: list[MerkleNode]) -> MerkleNode:
        self.layers.append(nodes)
        if len(nodes) == 1:
            return nodes[0]

        next_layer = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            combined_hash = self._hash_pair(left.hash, right.hash)
            next_layer.append(MerkleNode(hash=combined_hash, left=left, right=right))

        return self._build_recursive(next_layer)

    @property
    def root_hash(self) -> str | None:
        return self.root.hash if self.root else None

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Optimized path discovery (O(log N)) using the pre-built Merkle Tree structure."""
        if not self.root or not (0 <= index < len(self._leaves)):
            return []

        proof = []
        idx = index
        # We skip the last layer since it only contains the root
        for layer in self.layers[:-1]:
            sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if sibling_idx < len(layer):
                proof.append((layer[sibling_idx].hash, "R" if idx % 2 == 0 else "L"))
            else:
                # Duplication case
                proof.append((layer[idx].hash, "R"))
            idx //= 2
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: list[tuple[str, str]], root_hash: str) -> bool:
        current = leaf_hash
        for sibling_hash, direction in proof:
            if direction == "L":
                current = hashlib.sha256((sibling_hash + current).encode()).hexdigest()
            else:
                current = hashlib.sha256((current + sibling_hash).encode()).hexdigest()
        return current == root_hash


class SemanticMerkleTree:
    """Vectorial Merkle Tree — Validates integrity using semantic distance.

    Instead of comparing SHA-256 hashes of raw bytes, this tree compares
    the cosine similarity of embedding vectors. A paraphrased memory
    ("likes apples" → "prefers apples") passes validation at threshold 0.98,
    while a genuine hallucination ("likes apples" → "likes pears") fails.

    GPU-native: batch-generates fingerprints using CUDA when available.
    Edge-compatible: cosine comparison is O(D) with D=384, no deps.
    """

    def __init__(
        self,
        contents: list[str],
        embedder: Any = None,
        threshold: float = 0.98,
    ):
        from cortex.engine.semantic_hash import (
            SemanticFingerprint,
            batch_fingerprint,
        )

        self.threshold = threshold
        self._contents = contents

        if not contents:
            self.root = None
            self._fingerprints: list[SemanticFingerprint] = []
            self._classic_tree = None
            return

        # GPU-accelerated batch embedding
        self._fingerprints = batch_fingerprint(contents, embedder)

        # Build classic Merkle Tree from fingerprint hashes for O(log N) proofs
        leaf_hashes = [fp.hash for fp in self._fingerprints]
        self._classic_tree = MerkleTree(leaf_hashes)
        self.root = self._classic_tree.root

    @property
    def root_hash(self) -> str | None:
        return self._classic_tree.root_hash if self._classic_tree else None

    def verify_content(self, index: int, content: str, embedder: Any = None) -> dict:
        """Verify a single content entry against the tree using semantic distance.

        Returns a dict with:
          - valid: bool (passes semantic threshold)
          - similarity: float (cosine similarity)
          - exact_match: bool (byte-exact hash match)
          - threshold: float
        """
        from cortex.engine.semantic_hash import (
            cosine_similarity,
            semantic_fingerprint,
        )

        if not self._fingerprints or not (0 <= index < len(self._fingerprints)):
            return {
                "valid": False,
                "similarity": 0.0,
                "exact_match": False,
                "threshold": self.threshold,
                "error": "index_out_of_range",
            }

        stored_fp = self._fingerprints[index]
        current_fp = semantic_fingerprint(content, embedder)

        sim = cosine_similarity(stored_fp.embedding, current_fp.embedding)
        exact = stored_fp.hash == current_fp.hash

        return {
            "valid": sim >= self.threshold,
            "similarity": round(sim, 6),
            "exact_match": exact,
            "threshold": self.threshold,
        }

    def verify_batch(self, contents: list[str], embedder: Any = None) -> list[dict]:
        """Verify multiple content entries. GPU-accelerated via batch embedding."""
        from cortex.engine.semantic_hash import batch_fingerprint, cosine_similarity

        if not self._fingerprints:
            return []

        current_fps = batch_fingerprint(contents, embedder)
        results = []

        for i, (stored_fp, current_fp) in enumerate(
            zip(self._fingerprints, current_fps, strict=True)
        ):
            sim = cosine_similarity(stored_fp.embedding, current_fp.embedding)
            exact = stored_fp.hash == current_fp.hash
            results.append(
                {
                    "index": i,
                    "valid": sim >= self.threshold,
                    "similarity": round(sim, 6),
                    "exact_match": exact,
                    "threshold": self.threshold,
                }
            )

        return results


class SovereignLedger:
    """The Custodian of Immutable History (CORTEX Wave 5/8).

    Unified implementation supporting both synchronous single-connection
    and asynchronous pool-based operations. Implements adaptive
    checkpointing and v2 canonical hashing.
    """

    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, db: sqlite3.Connection | aiosqlite.Connection | CortexConnectionPool):
        from cortex import config

        self.db = db
        self._write_timestamps: deque[float] = deque(maxlen=5000)
        self._lock = asyncio.Lock()
        self._config = config

        # Schema is created synchronously on init if possible
        if self._is_sync_connection(db):
            self._ensure_schema_sync(cast(sqlite3.Connection, db))

    @staticmethod
    def _is_sync_connection(db: object) -> bool:
        """Return true for sqlite-compatible synchronous connections.

        Some test/runtime wrappers expose the sqlite3 connection protocol
        without preserving a strict ``sqlite3.Connection`` identity.
        """
        if isinstance(db, aiosqlite.Connection):
            return False
        return isinstance(db, sqlite3.Connection) or all(
            hasattr(db, attr) for attr in ("execute", "commit", "rollback")
        )

    def _sync_db(self) -> sqlite3.Connection:
        if not self._is_sync_connection(self.db):
            raise RuntimeError("operation requires a sync sqlite3.Connection")
        return cast(sqlite3.Connection, self.db)

    def _ensure_schema_sync(self, conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       TEXT NOT NULL DEFAULT '__global__',
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type      TEXT NOT NULL,
                status          TEXT NOT NULL,
                details         TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_prev ON transactions(prev_hash);
            CREATE INDEX IF NOT EXISTS idx_merkle_range ON merkle_roots(tx_start_id, tx_end_id);
        """)
        self._ensure_ledger_column(
            conn,
            "transactions",
            "tenant_id",
            "TEXT NOT NULL DEFAULT 'default'",
        )
        self._ensure_ledger_column(
            conn,
            "merkle_roots",
            "tenant_id",
            "TEXT NOT NULL DEFAULT '__global__'",
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_tenant_id ON transactions(tenant_id, id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_merkle_tenant_range "
            "ON merkle_roots(tenant_id, tx_start_id, tx_end_id)"
        )

    @staticmethod
    def _ensure_ledger_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def record_write(self) -> None:
        """Track write rate for adaptive checkpointing."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW if self._write_timestamps else 0
        if rate > self.HIGH_WRITE_THRESHOLD:
            return getattr(self._config, "CHECKPOINT_MIN", 10)
        return getattr(self._config, "CHECKPOINT_MAX", 100)

    @staticmethod
    def _effective_tenant_id(tenant_id: str | None) -> str:
        return tenant_id or "default"

    def record_transaction(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction synchronously."""
        conn = self._sync_db()

        self.record_write()
        detail_json = canonical_json(detail) if detail else "{}"
        ts = now_iso()
        effective_tenant_id = self._effective_tenant_id(tenant_id)

        try:
            conn.execute("BEGIN EXCLUSIVE")
            new_hash = self._record_transaction_sync_unlocked(
                conn,
                project,
                action,
                detail_json,
                ts,
                effective_tenant_id,
            )
            conn.commit()
            return new_hash
        except sqlite3.Error:
            conn.rollback()
            raise

    def record_transaction_in_current_transaction(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction inside the caller's active SQLite transaction."""
        conn = self._sync_db()

        self.record_write()
        return self._record_transaction_sync_unlocked(
            conn,
            project,
            action,
            canonical_json(detail) if detail else "{}",
            now_iso(),
            self._effective_tenant_id(tenant_id),
        )

    def _record_transaction_sync_unlocked(
        self,
        conn: sqlite3.Connection,
        project: str,
        action: str,
        detail_json: str,
        timestamp: str,
        tenant_id: str,
    ) -> str:
        cursor = conn.execute(
            "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        row = cursor.fetchone()
        prev_hash = row[0] if row else "GENESIS"
        new_hash = compute_tx_hash(prev_hash, project, action, detail_json, timestamp, tenant_id)
        conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, tenant_id, timestamp)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project, action, detail_json, prev_hash, new_hash, tenant_id, timestamp),
        )
        return new_hash

    async def record_transaction_async(
        self,
        project: str,
        action: str,
        detail: Any = None,
        tenant_id: str | None = None,
    ) -> str:
        """Record a transaction asynchronously (requires a connection pool)."""
        self.record_write()
        detail_json = canonical_json(detail) if detail else "{}"
        ts = now_iso()
        effective_tenant_id = self._effective_tenant_id(tenant_id)

        async with self._get_conn_proxy() as conn:  # type: ignore[reportAttributeAccessIssue]
            await conn.execute("BEGIN EXCLUSIVE")
            try:
                cursor = await conn.execute(
                    "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                    (effective_tenant_id,),
                )
                row = await cursor.fetchone()
                prev_hash = row[0] if row else "GENESIS"
                new_hash = compute_tx_hash(
                    prev_hash,
                    project,
                    action,
                    detail_json,
                    ts,
                    effective_tenant_id,
                )

                await conn.execute(
                    "INSERT INTO transactions "
                    "(project, action, detail, prev_hash, hash, tenant_id, timestamp)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (project, action, detail_json, prev_hash, new_hash, effective_tenant_id, ts),
                )
                await conn.commit()
                return new_hash
            except (aiosqlite.Error, sqlite3.Error, TypeError, ValueError):
                await conn.rollback()
                raise

    def create_checkpoint(self) -> str | None:
        """Create a Merkle checkpoint synchronously."""
        if not self._is_sync_connection(self.db):
            return None
        conn = self._sync_db()

        batch_size = self.adaptive_batch_size
        cursor = conn.execute(
            "SELECT MAX(tx_end_id) FROM merkle_roots WHERE tenant_id = '__global__'"
        )
        row = cursor.fetchone()
        last_covered = row[0] or 0 if row else 0

        cursor = conn.execute(
            "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id LIMIT ?",
            (last_covered, batch_size),
        )
        rows = cursor.fetchall()

        if not rows or len(rows) < batch_size:
            return None

        hashes = [r[1] for r in rows]
        tree = MerkleTree(hashes)
        root = tree.root_hash
        start_id, end_id = rows[0][0], rows[-1][0]

        conn.execute(
            "INSERT INTO merkle_roots "
            "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
            "VALUES ('__global__', ?, ?, ?, ?)",
            (root, start_id, end_id, len(rows)),
        )
        conn.commit()
        return root

    async def create_checkpoint_async(self) -> str | None:
        """Create a Merkle checkpoint asynchronously."""
        batch_size = self.adaptive_batch_size

        async with self._lock:
            async with self._get_conn_proxy() as conn:  # type: ignore[reportAttributeAccessIssue]
                cursor = await conn.execute(
                    "SELECT MAX(tx_end_id) FROM merkle_roots WHERE tenant_id = '__global__'"
                )
                row = await cursor.fetchone()
                last_covered = row[0] or 0 if row else 0

                cursor = await conn.execute(
                    "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id LIMIT ?",
                    (last_covered, batch_size),
                )
                rows = list(await cursor.fetchall())

                if not rows or len(rows) < batch_size:
                    return None

                hashes = [r[1] for r in rows]
                tree = MerkleTree(hashes)
                root = tree.root_hash
                start_id, end_id = rows[0][0], rows[-1][0]

                await conn.execute(
                    "INSERT INTO merkle_roots "
                    "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
                    "VALUES ('__global__', ?, ?, ?, ?)",
                    (root, start_id, end_id, len(rows)),
                )
                await conn.commit()
                return root

    @asynccontextmanager
    async def _get_conn_proxy(self) -> AsyncIterator[aiosqlite.Connection]:
        """Internal helper to get a connection for auditing/writing,
        supporting both Pool and raw Connection (Ω₁).
        """
        if isinstance(self.db, aiosqlite.Connection):
            yield self.db
            return

        if self._is_sync_connection(self.db):
            raise RuntimeError("Async ledger operations require a CortexConnectionPool backend")

        pool = cast("CortexConnectionPool", self.db)
        async with pool.acquire() as conn:
            yield conn

    async def audit_integrity_async(self, tenant_id: str | None = None) -> dict:
        """Perform a full integrity audit asynchronously (Ω₁)."""
        violations = []
        tx_count = 0

        async with self._get_conn_proxy() as conn:
            started_at = now_iso()
            cursor = await conn.execute(
                "SELECT id, COALESCE(tenant_id, 'default'), project, action, detail, "
                "prev_hash, hash, timestamp FROM transactions ORDER BY id"
            )

            expected_prev_by_tenant: dict[str, str] = {}
            expected_prev_global = "GENESIS"
            while True:
                row = await cursor.fetchone()
                if not row:
                    break
                tid, tx_tenant_id, proj, act, det, prev, h, ts = row
                in_scope = tenant_id is None or tx_tenant_id == tenant_id

                expected_prev = expected_prev_by_tenant.get(tx_tenant_id, "GENESIS")
                computed_v3 = compute_tx_hash(prev, proj, act, det, ts, tenant_id=tx_tenant_id)
                computed_v2 = compute_tx_hash(prev, proj, act, det, ts)
                computed_v1 = compute_tx_hash_v1(prev, proj, act, det, ts)

                if in_scope:
                    tx_count += 1
                    if computed_v3 == h:
                        if prev != expected_prev:
                            violations.append(
                                {"id": tid, "type": "CHAIN_BREAK", "expected": expected_prev}
                            )
                    elif h in {computed_v2, computed_v1}:
                        if prev != expected_prev_global:
                            violations.append(
                                {
                                    "id": tid,
                                    "type": "CHAIN_BREAK",
                                    "expected": expected_prev,
                                    "legacy_expected": expected_prev_global,
                                }
                            )
                    else:
                        violations.append({"id": tid, "type": "TAMPER_DETECTED", "stored": h})

                expected_prev_by_tenant[tx_tenant_id] = h
                expected_prev_global = h
                if tid % 100 == 0:
                    await asyncio.sleep(0)  # Yield

            # Verify Merkle Roots
            if tenant_id is None:
                cursor = await conn.execute(
                    "SELECT COALESCE(tenant_id, 'default'), root_hash, tx_start_id, tx_end_id "
                    "FROM merkle_roots"
                )
            else:
                cursor = await conn.execute(
                    "SELECT COALESCE(tenant_id, 'default'), root_hash, tx_start_id, tx_end_id "
                    "FROM merkle_roots WHERE tenant_id = ?",
                    (tenant_id,),
                )
            roots = list(await cursor.fetchall())
            for root_tenant_id, stored_root, start, end in roots:
                if root_tenant_id == "__global__":
                    c = await conn.execute(
                        "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                        (start, end),
                    )
                else:
                    c = await conn.execute(
                        "SELECT hash FROM transactions "
                        "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                        (root_tenant_id, start, end),
                    )
                hashes = [r[0] for r in list(await c.fetchall())]
                computed_root = MerkleTree(hashes).root_hash
                if computed_root != stored_root:
                    violations.append({"range": f"{start}-{end}", "type": "MERKLE_MISMATCH"})

            status = "ok" if not violations else "violation"
            await conn.execute(
                "INSERT INTO integrity_checks (check_type, status, details, started_at, completed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "full" if tenant_id is None else "tenant",
                    status,
                    json.dumps(violations),
                    started_at,
                    now_iso(),
                ),
            )
            await conn.commit()

        return {"valid": not violations, "violations": violations, "tx_count": tx_count}
