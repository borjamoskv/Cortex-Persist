from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex import config
from cortex.utils.canonical import compute_tx_hash

__all__ = ["SovereignLedger"]

logger = logging.getLogger("cortex.ledger.sovereign")

@dataclass(frozen=True)
class MerkleNode:
    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False

class MerkleTree:
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
    """Unified Wave 8 Sovereign Ledger."""

    WRITE_RATE_WINDOW = 60
    HIGH_WRITE_THRESHOLD = 10

    def __init__(self, db: Any = None, genesis_hash: str | None = None):
        self.pool = db
        self._write_timestamps: deque[float] = deque(maxlen=5000)
        # Ω1 Byzantine Genesis: Allow external anchor (e.g. CORTEX_LEDGER_ANCHOR)
        anchor = os.getenv("CORTEX_LEDGER_ANCHOR")
        if not anchor:
            logger.warning("Ω1_WARNING: CORTEX_LEDGER_ANCHOR not found. Using default 'GENESIS'. Internal entropy risk.")
        
        self._genesis_hash = genesis_hash or anchor or "GENESIS"
        self._last_hash = self._genesis_hash

    async def ensure_table(self):
        async with self._acquire_conn() as conn:
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS transactions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    project         TEXT,
                    action          TEXT,
                    detail          TEXT,
                    prev_hash       TEXT,
                    hash            TEXT,
                    timestamp       TEXT,
                    tenant_id       TEXT NOT NULL DEFAULT 'default',
                    UNIQUE(hash, tenant_id)
                )"""
            )
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS merkle_roots (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id       TEXT NOT NULL DEFAULT 'default',
                    root_hash       TEXT NOT NULL,
                    tx_start_id     INTEGER NOT NULL,
                    tx_end_id       INTEGER NOT NULL,
                    tx_count        INTEGER NOT NULL,
                    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
                )"""
            )
            await conn.commit()

    @asynccontextmanager
    async def _acquire_conn(self) -> AsyncIterator[aiosqlite.Connection]:
        """Helper to handle both pool and direct connection types."""
        if not self.pool:
            raise RuntimeError("Ledger not initialized.")

        if hasattr(self.pool, "session"):
            # It's an engine
            async with self.pool.session() as conn:
                yield conn
        elif isinstance(self.pool, aiosqlite.Connection):
            # It's a direct connection
            yield self.pool
        else:
            pool = cast("CortexConnectionPool", self.pool)
            async with pool.acquire() as conn:
                yield conn

    def record_write_metric(self) -> None:
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
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
        detail_json = json.dumps(detail, sort_keys=True)
        ts = datetime.now(timezone.utc).isoformat()
        self.record_write_metric()

        async with self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
                (tenant_id,),
            )
            row = await cursor.fetchone()
            prev_hash = str(row[0]) if row and row[0] else self._genesis_hash
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

    async def audit_integrity(self, tenant_id: str = "default") -> dict[str, Any]:
        violations = []
        tx_count = 0
        async with self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT id, project, action, detail, prev_hash, hash, timestamp "
                "FROM transactions WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            )
            expected_prev = self._genesis_hash
            async for row in cursor:
                tid, proj, act, det, prev, h, ts = row
                tx_count += 1
                if prev != expected_prev:
                    violations.append({"id": tid, "type": "CHAIN_BREAK"})
                computed = compute_tx_hash(prev, proj, act, det, ts)
                if computed != h:
                    violations.append({"id": tid, "type": "TAMPER_DETECTED"})
                expected_prev = h
        return {"valid": not violations, "violations": violations, "tx_count": tx_count}

    async def verify_integrity_async(self, tenant_id: str = "default") -> dict[str, Any]:
        """Verify the transaction hash chain and persisted Merkle checkpoints."""
        tx_report = await self.audit_integrity(tenant_id=tenant_id)
        violations = list(tx_report["violations"])

        async with self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT id, root_hash, tx_start_id, tx_end_id "
                "FROM merkle_roots WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            )
            roots = list(await cursor.fetchall())

            for root_id, root_hash, start_id, end_id in roots:
                tx_cursor = await conn.execute(
                    "SELECT hash FROM transactions "
                    "WHERE tenant_id = ? AND id >= ? AND id <= ? ORDER BY id",
                    (tenant_id, start_id, end_id),
                )
                hashes = [str(row[0]) for row in await tx_cursor.fetchall()]
                if MerkleTree(hashes).root != root_hash:
                    violations.append(
                        {
                            "id": root_id,
                            "type": "MERKLE_ROOT_MISMATCH",
                            "start": start_id,
                            "end": end_id,
                        }
                    )

        return {
            "valid": not violations,
            "violations": violations,
            "tx_checked": tx_report["tx_count"],
            "roots_checked": len(roots),
        }

    async def create_checkpoint_async(self, tenant_id: str = "default") -> int | None:
        """Create a Merkle checkpoint for the next uncovered transaction batch."""
        async with self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT MAX(tx_end_id) FROM merkle_roots WHERE tenant_id = ?",
                (tenant_id,),
            )
            row = await cursor.fetchone()
            last_covered = int(row[0]) if row and row[0] is not None else 0

            tx_cursor = await conn.execute(
                "SELECT id, hash FROM transactions WHERE tenant_id = ? AND id > ? ORDER BY id LIMIT ?",
                (tenant_id, last_covered, self.adaptive_batch_size),
            )
            rows = list(await tx_cursor.fetchall())

            if len(rows) < self.adaptive_batch_size:
                return None

            hashes = [str(row[1]) for row in rows]
            start_id = int(rows[0][0])
            end_id = int(rows[-1][0])
            root_hash = MerkleTree(hashes).root

            insert_cursor = await conn.execute(
                "INSERT INTO merkle_roots "
                "(tenant_id, root_hash, tx_start_id, tx_end_id, tx_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (tenant_id, root_hash, start_id, end_id, len(rows)),
            )
            await conn.commit()
            return int(insert_cursor.lastrowid) if insert_cursor.lastrowid is not None else None
