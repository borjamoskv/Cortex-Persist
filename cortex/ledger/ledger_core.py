"""
CORTEX v8 — Sovereign Immutable Ledger (CHRONOS-1 Standard).

Axiom Reference:
- Ω₃ (Byzantine Default): "I verify, then trust. Never reversed."
- Ω₂ (Entropic Asymmetry): "Merkle Trees reduce trust-cost from O(N) to O(log N)."
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("cortex.ledger")


@dataclass(frozen=True)
class MerkleNode:
    """A node within the Merkle Tree (V8 Immutable)."""

    hash: str
    left: Optional[MerkleNode] = None
    right: Optional[MerkleNode] = None
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
    def root_hash(self) -> Optional[str]:
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
    def root_hash(self) -> Optional[str]:
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
    """The Custodian of Immutable History (CORTEX Wave 5)."""

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_tx_prev ON transactions(prev_hash);
            CREATE INDEX IF NOT EXISTS idx_merkle_range ON merkle_roots(tx_start_id, tx_end_id);
        """)

    def _compute_tx_hash(
        self, prev_hash: str, project: str, action: str, detail: str, ts: Any
    ) -> str:
        ts_str = str(ts)
        payload = f"{prev_hash}:{project}:{action}:{detail}:{ts_str}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def record_transaction(self, project: str, action: str, detail: Any = None) -> str:
        detail_json = json.dumps(detail, sort_keys=True) if detail else "{}"
        ts = datetime.now(timezone.utc).isoformat()

        try:
            # Enforce an EXCLUSIVE lock to prevent race conditions (Chain Forking)
            # during the read-compute-write cycle of the hash chain.
            self.conn.execute("BEGIN EXCLUSIVE")

            cursor = self.conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row[0] if row else "GENESIS"
            new_hash = self._compute_tx_hash(prev_hash, project, action, detail_json, ts)

            self.conn.execute(
                "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (project, action, detail_json, prev_hash, new_hash, ts),
            )
            self.conn.commit()
            return new_hash
        except sqlite3.IntegrityError as e:
            logger.error("Ledger collision or duplicate: %s", e)
            raise
        except sqlite3.Error as e:
            logger.error("Ledger OS/IO Failure: %s", e)
            raise

    def create_checkpoint(self, batch_size: int = 100) -> Optional[str]:
        cursor = self.conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
        last_covered = cursor.fetchone()[0] or 0
        cursor = self.conn.execute(
            "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id", (last_covered,)
        )
        rows = cursor.fetchall()
        if not rows or (len(rows) < batch_size and last_covered > 0):
            return None
        hashes = [r[1] for r in rows]
        tree = MerkleTree(hashes)
        root = tree.root_hash
        start_id, end_id = rows[0][0], rows[-1][0]
        self.conn.execute(
            "INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count) VALUES (?, ?, ?, ?)",
            (root, start_id, end_id, len(rows)),
        )
        self.conn.commit()
        return root

    def audit_integrity(self) -> dict:
        violations = []
        cursor = self.conn.execute(
            "SELECT id, project, action, detail, prev_hash, hash, timestamp FROM transactions ORDER BY id"
        )
        expected_prev = "GENESIS"
        tx_count = 0

        # Iterate over the cursor directly (streaming) instead of `fetchall()` to prevent OOM
        for row in cursor:
            tid, proj, act, det, prev, h, ts = row
            tx_count += 1
            if prev != expected_prev:
                violations.append(
                    {"id": tid, "type": "CHAIN_BREAK", "expected": expected_prev, "actual": prev}
                )
            computed = self._compute_tx_hash(prev, proj, act, det, ts)
            if computed != h:
                violations.append(
                    {"id": tid, "type": "TAMPER_DETECTED", "stored": h, "computed": computed}
                )
            expected_prev = h
        cursor = self.conn.execute("SELECT root_hash, tx_start_id, tx_end_id FROM merkle_roots")
        for stored_root, start, end in cursor.fetchall():
            c = self.conn.execute(
                "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id", (start, end)
            )
            hashes = [r[0] for r in c.fetchall()]
            computed_root = MerkleTree(hashes).root_hash
            if computed_root != stored_root:
                violations.append(
                    {"range": f"{start}-{end}", "type": "MERKLE_MISMATCH", "stored": stored_root}
                )
        return {"valid": not violations, "violations": violations, "tx_count": tx_count}
