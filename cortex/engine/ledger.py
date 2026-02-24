"""
CORTEX v5.0 — Immutable Ledger with Adaptive Checkpointing.

Cryptographic integrity for the CORTEX transaction ledger using Merkle Trees.
Enables efficient batch verification and tamper-proof auditing.

Adaptive checkpointing: reduces batch size during high write-rate periods
(e.g., swarm bursts) to minimize data loss on crash.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex.utils.canonical import compute_tx_hash, compute_tx_hash_v1
from cortex import config
from cortex.consensus.merkle import MerkleTree

__all__ = ["ImmutableLedger"]

logger = logging.getLogger("cortex")


class ImmutableLedger:
    """
    Manages the cryptographic integrity of the CORTEX transaction ledger.

    Adaptive checkpointing: batch size shrinks during high write-rate
    periods (swarm bursts) and returns to normal during calm periods.
    """

    CHECKPOINT_BATCH_SIZE = config.CHECKPOINT_MAX  # Legacy compat (class attribute)
    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, pool: CortexConnectionPool):
        self.pool = pool
        self._write_timestamps: deque[float] = deque(maxlen=5000)

    def record_write(self) -> None:
        """Call on every transaction to track write rate."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW
        if rate > self.HIGH_WRITE_THRESHOLD:
            return config.CHECKPOINT_MIN
        return config.CHECKPOINT_MAX

    async def compute_merkle_root_async(
        self, start_id: int, end_id: int, conn=None
    ) -> str | None:
        """Compute Merkle root for a range of transactions (async).

        Args:
            start_id: First transaction ID in range (inclusive).
            end_id: Last transaction ID in range (inclusive).
            conn: Optional existing connection. If provided, reuses it
                  to avoid double-acquisition deadlocks (D004).
        """
        async def _compute(c):
            cursor = await c.execute(
                "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                (start_id, end_id),
            )
            rows = await cursor.fetchall()
            hashes = [row[0] for row in rows]
            if not hashes:
                return None
            tree = MerkleTree(hashes)
            return tree.root

        if conn is not None:
            return await _compute(conn)
        async with self.pool.acquire() as acquired_conn:
            return await _compute(acquired_conn)

    async def create_checkpoint_async(self) -> int | None:
        """Create a Merkle tree checkpoint for recent transactions (async)."""
        batch_size = self.adaptive_batch_size

        async with self.pool.acquire() as conn:
            # Find last checkpointed transaction
            cursor = await conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
            row = await cursor.fetchone()
            last_tx = row[0] or 0 if row else 0

            # Count pending transactions
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,)
            )
            row = await cursor.fetchone()
            pending = row[0] if row else 0

            if pending < batch_size:
                return None

            start_id = last_tx + 1
            # Get the ID of the N-th transaction from start
            cursor = await conn.execute(
                "SELECT id FROM transactions WHERE id >= ? ORDER BY id LIMIT 1 OFFSET ?",
                (start_id, batch_size - 1),
            )
            end_row = await cursor.fetchone()

            if not end_row:
                return None

            end_id = end_row[0]

            # D004 FIX: Pass existing conn to avoid double pool acquisition
            root_hash = await self.compute_merkle_root_async(start_id, end_id, conn=conn)

            if not root_hash:
                return None

            cursor = await conn.execute(
                """
                INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count)
                VALUES (?, ?, ?, ?)
                """,
                (root_hash, start_id, end_id, batch_size),
            )
            await conn.commit()
            logger.info(
                "Created Merkle checkpoint #%d (TX %d-%d)", cursor.lastrowid, start_id, end_id
            )
            return cursor.lastrowid

    def compute_merkle_root_sync(self, conn, start_id: int, end_id: int) -> str | None:
        """Compute Merkle root for a range of transactions synchronously."""
        cursor = conn.execute(
            "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id ASC",
            (start_id, end_id),
        )
        hashes = [row[0] for row in cursor.fetchall()]
        if not hashes:
            return None
        tree = MerkleTree(hashes)
        return tree.root

    def create_checkpoint_sync(self, conn=None) -> int | None:
        """Create a Merkle tree checkpoint for recent transactions synchronously."""
        batch_size = self.adaptive_batch_size

        # If no conn provided, we can't easily get one if we only have a pool
        # For sync usage, the caller should provide the connection.
        if conn is None:
            if hasattr(self.pool, "_get_sync_conn"):
                conn = self.pool._get_sync_conn()
            else:
                # Last resort — if pool has a db_path attribute (CortexEngine does)
                logger.warning("No sync connection provided to create_checkpoint_sync")
                return None

        # Find last checkpointed transaction
        cursor = conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
        row = cursor.fetchone()
        last_tx = row[0] or 0 if row else 0

        # Count pending transactions
        cursor = conn.execute("SELECT COUNT(*) FROM transactions WHERE id > ?", (last_tx,))
        row = cursor.fetchone()
        pending = row[0] if row else 0

        if pending < batch_size:
            return None

        start_id = last_tx + 1
        # Get the ID of the N-th transaction from start
        cursor = conn.execute(
            "SELECT id FROM transactions WHERE id >= ? ORDER BY id LIMIT 1 OFFSET ?",
            (start_id, batch_size - 1),
        )
        end_row = cursor.fetchone()

        if not end_row:
            return None

        end_id = end_row[0]
        root_hash = self.compute_merkle_root_sync(conn, start_id, end_id)

        if not root_hash:
            return None

        cursor = conn.execute(
            """
            INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count)
            VALUES (?, ?, ?, ?)
            """,
            (root_hash, start_id, end_id, batch_size),
        )
        conn.commit()
        logger.info(
            "Created Merkle checkpoint #%d (TX %d-%d) [sync]", cursor.lastrowid, start_id, end_id
        )
        return cursor.lastrowid

    async def verify_integrity_async(self) -> dict:
        """Verify hash chain continuity and Merkle checkpoints (async)."""
        violations = []
        tx_count = 0

        async with self.pool.acquire() as conn:
            # 1. Verify Hash Chain (Chunked to avoid OOM)
            cursor = await conn.execute(
                "SELECT id, prev_hash, hash, project, action, detail, timestamp FROM transactions ORDER BY id"
            )

            current_prev = "GENESIS"
            while True:
                tx = await cursor.fetchone()
                if not tx:
                    break

                tx_id, p_hash, c_hash, proj, act, detail, ts = tx
                tx_count += 1

                if p_hash != current_prev:
                    violations.append(
                        {
                            "tx_id": tx_id,
                            "type": "chain_break",
                            "expected": current_prev,
                            "actual": p_hash,
                        }
                    )

                # Recompute hash — try v2 (canonical) first, fallback to v1 (legacy)
                computed_v2 = compute_tx_hash(p_hash, proj, act, detail, ts)
                computed_v1 = compute_tx_hash_v1(p_hash, proj, act, detail, ts)
                if computed_v2 != c_hash and computed_v1 != c_hash:
                    violations.append(
                        {
                            "tx_id": tx_id,
                            "type": "hash_mismatch",
                            "computed_v2": computed_v2,
                            "computed_v1": computed_v1,
                            "stored": c_hash,
                        }
                    )
                current_prev = c_hash

            # 2. Verify Merkle Checkpoints
            cursor = await conn.execute(
                "SELECT id, root_hash, tx_start_id, tx_end_id FROM merkle_roots ORDER BY id"
            )
            roots = await cursor.fetchall()

            for m_id, r_hash, start, end in roots:
                # We reuse the same compute method
                computed_r = await self.compute_merkle_root_async(start, end, conn=conn)
                if computed_r != r_hash:
                    violations.append(
                        {
                            "merkle_id": m_id,
                            "type": "merkle_mismatch",
                            "expected": r_hash,
                            "actual": computed_r,
                        }
                    )

            status = "ok" if not violations else "violation"

            if violations:
                logger.error(f"Integrity check failed: {len(violations)} violations found")

            # Record check
            await conn.execute(
                "INSERT INTO integrity_checks (check_type, status, details, started_at, completed_at) VALUES (?, ?, ?, ?, ?)",
                (
                    "full",
                    status,
                    json.dumps(violations),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()

            return {
                "valid": not violations,
                "violations": violations,
                "tx_checked": tx_count,
                "roots_checked": len(roots),
            }
