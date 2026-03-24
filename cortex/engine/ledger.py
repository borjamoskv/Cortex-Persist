from __future__ import annotations

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass

import aiosqlite

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex import config
from cortex.utils.canonical import compute_tx_hash

__all__ = ["SovereignLedger", "ImmutableLedger"]

logger = logging.getLogger("cortex.engine.ledger")

@dataclass(frozen=True)
class MerkleNode:
    """A node within the Merkle Tree (V8 Immutable)."""

    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False


class MerkleTree:
    """Merkle Tree implementation for Ω-Checkpoints."""

    def __init__(self, hashes: list[str]):
        self.leaves = [MerkleNode(h, is_leaf=True) for h in hashes]
        if not self.leaves:
            self.root_node = MerkleNode("GENESIS")
        else:
            self.root_node = self._build_tree(self.leaves)

    @property
    def root(self) -> str:
        return self.root_node.hash

    def _build_tree(self, nodes: list[MerkleNode]) -> MerkleNode:
        if len(nodes) == 1:
            return nodes[0]
        
        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else left
            combined_hash = compute_tx_hash(left.hash, "merkle", "combine", right.hash, "")
            next_level.append(MerkleNode(combined_hash, left, right))
            
        return self._build_tree(next_level)


class SovereignLedger:
    """
    Sovereign Ledger Implementation with Merkle Proofs and hash chaining (Ω₃).
    Unified CORTEX Wave 8 logic.
    """

    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, db: CortexConnectionPool | aiosqlite.Connection | None = None):
        self.pool = db  # Map db to pool for compatibility with MCP
        self._write_timestamps: deque[float] = deque(maxlen=5000)
        self._last_hash = "GENESIS"

    async def _acquire_conn(self):
        """Helper to handle both pool and direct connection types."""
        if not self.pool:
            raise RuntimeError("Ledger not initialized with a database connection.")
        
        if hasattr(self.pool, "acquire"):
            return self.pool.acquire()
        # For direct connection, we use a dummy context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def dummy():
            yield self.pool
        return dummy()

    def record_write_metric(self) -> None:
        """Track write rate for adaptive checkpointing."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW if self.WRITE_RATE_WINDOW > 0 else 0
        if rate > self.HIGH_WRITE_THRESHOLD:
            return getattr(config, "LEDGER_CHECKPOINT_MIN", 10)
        return getattr(config, "LEDGER_CHECKPOINT_MAX", 100)

    async def record_transaction(
        self, project: str, action: str, detail: dict[str, Any], tenant_id: str = "default"
    ) -> str:
        """Commit a high-value decision into deterministic history."""
        detail_json = json.dumps(detail, sort_keys=True)
        ts = datetime.now(timezone.utc).isoformat()
        self.record_write_metric()

        async with await self._acquire_conn() as conn:
            # Find prev_hash safely
            cursor = await conn.execute(
                "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            prev_hash = row[0] if row else "GENESIS"

            tx_hash = compute_tx_hash(prev_hash, project, action, detail_json, ts)
            
            await conn.execute(
                """INSERT INTO transactions 
                   (project, action, detail, prev_hash, hash, timestamp, tenant_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project, action, detail_json, prev_hash, tx_hash, ts, tenant_id)
            )
            await conn.commit()
            self._last_hash = tx_hash
            return tx_hash

    async def create_checkpoint(self) -> str | None:
        """Adaptive Merkle checkpointing."""
        batch_size = self.adaptive_batch_size

        async with await self._acquire_conn() as conn:
            cursor = await conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
            row = await cursor.fetchone()
            last_covered = row[0] if row and row[0] else 0

            cursor = await conn.execute(
                "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id", (last_covered,)
            )
            rows = await cursor.fetchall()
            if not rows or (len(rows) < batch_size and last_covered > 0):
                return None

            hashes = [r[1] for r in rows]
            tree = MerkleTree(hashes)
            root = tree.root
            start_id, end_id = rows[0][0], rows[-1][0]

            await conn.execute(
                "INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count) VALUES (?, ?, ?, ?)",
                (root, start_id, end_id, len(rows)),
            )
            await conn.commit()
            logger.info("Created Merkle checkpoint (TX %d-%d)", start_id, end_id)
            return root

    async def audit_integrity(self) -> dict[str, Any]:
        """Verify hash chain and Merkle roots."""
        violations = []
        tx_count = 0
        async with await self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT id, project, action, detail, prev_hash, hash, timestamp FROM transactions ORDER BY id"
            )
            expected_prev = "GENESIS"
            async for row in cursor:
                tid, proj, act, det, prev, h, ts = row
                tx_count += 1
                if prev != expected_prev:
                    violations.append({"id": tid, "type": "CHAIN_BREAK"})
                computed = compute_tx_hash(prev, proj, act, det, ts)
                if computed != h:
                    violations.append({"id": tid, "type": "TAMPER_DETECTED"})
                expected_prev = h

            # Check roots
            cursor = await conn.execute("SELECT root_hash, tx_start_id, tx_end_id FROM merkle_roots")
            async for root_hash, start, end in cursor:
                c = await conn.execute(
                    "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                    (start, end),
                )
                hashes = [r[0] for r in await c.fetchall()]
                if MerkleTree(hashes).root != root_hash:
                    violations.append({"type": "MERKLE_ROOT_MISMATCH", "start": start, "end": end})

        return {
            "valid": not violations, 
            "violations": violations, 
            "tx_count": tx_count,
            "tx_checked": tx_count,
            "roots_checked": tx_count // 100 # Approx
        }

    async def get_transactions(self, project: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve recent transactions."""
        async with await self._acquire_conn() as conn:
            query = "SELECT id, project, action, detail, hash, timestamp FROM transactions"
            params = []
            if project:
                query += " WHERE project = ?"
                params.append(project)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            
            cursor = await conn.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0], "project": r[1], "action": r[2], 
                    "detail": json.loads(r[3]), "hash": r[4], "timestamp": r[5]
                }
                for r in rows
            ]

class ImmutableLedger(SovereignLedger):
    """Read-only view of the ledger for audit purposes."""
    
    def __init__(self, db: CortexConnectionPool | aiosqlite.Connection | None = None):
        super().__init__(db)
        self._write_lock = True

    async def record_transaction(self, project: str, action: str, detail: dict[str, Any], tenant_id: str = "default") -> str:
        raise PermissionError("Ledger is in read-only immutable mode.")
