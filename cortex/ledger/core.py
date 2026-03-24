from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .merkle import MerkleTree

logger = logging.getLogger(__name__)

class SovereignLedger:
    """
    The Custodian of Immutable History (CORTEX Wave 5).
    Refactored as a core component for sovereign persistence.
    """

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Initialize the cryptographic registry tables."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                project TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT,
                prev_hash TEXT,
                hash TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS merkle_roots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tx_start_id INTEGER,
                tx_end_id INTEGER,
                root_hash TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def _get_last_hash(self) -> str:
        cursor = self.conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else "0" * 64

    def record_transaction(self, project: str, action: str, detail: dict[str, Any]) -> str:
        """Record a validated event into the hash chain."""
        prev_hash = self._get_last_hash()
        timestamp = datetime.now(timezone.utc).isoformat()
        detail_json = json.dumps(detail, sort_keys=True, default=str)
        
        # Chain hash: sha256(prev_hash + timestamp + detail)
        payload = f"{prev_hash}{timestamp}{detail_json}"
        new_hash = hashlib.sha256(payload.encode()).hexdigest()
        
        try:
            self.conn.execute(
                "INSERT INTO transactions (timestamp, project, action, detail, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
                (timestamp, project, action, detail_json, prev_hash, new_hash)
            )
            self.conn.commit()
            return new_hash
        except sqlite3.Error as e:
            logger.error("Ledger OS/IO Failure: %s", e)
            raise

    def get_transactions(self, project: str | None = None) -> list[tuple]:
        """Retrieve transactions from the ledger, optionally filtered by project."""
        query = "SELECT id, timestamp, action, detail, prev_hash, hash FROM transactions"
        params = []
        if project:
            query += " WHERE project = ?"
            params.append(project)
        query += " ORDER BY id ASC"
        
        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def create_checkpoint(self, batch_size: int = 100) -> str | None:
        """Generate a Merkle Root for recent transactions to anchor history."""
        cursor = self.conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
        last_covered = cursor.fetchone()[0] or 0
        
        cursor = self.conn.execute(
            "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id ASC LIMIT ?",
            (last_covered, batch_size)
        )
        rows = cursor.fetchall()
        
        if not rows:
            return None
            
        tx_hashes = [r[1] for r in rows]
        start_id = rows[0][0]
        end_id = rows[-1][0]
        
        tree = MerkleTree(tx_hashes)
        root_hash = tree.root_hash
        
        if root_hash:
            self.conn.execute(
                "INSERT INTO merkle_roots (timestamp, tx_start_id, tx_end_id, root_hash) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), start_id, end_id, root_hash)
            )
            self.conn.commit()
            
        return root_hash

    def audit_integrity(self) -> bool:
        """Perform a full cryptographic audit of the chain."""
        cursor = self.conn.execute("SELECT id, prev_hash, timestamp, detail, hash FROM transactions ORDER BY id ASC")
        rows = cursor.fetchall()
        
        current_prev = "0" * 64
        for row_id, prev_hash, ts, detail, h in rows:
            if prev_hash != current_prev:
                logger.error("Chain broken at ID %d: Expected prev_hash %s, found %s", row_id, current_prev, prev_hash)
                return False
            
            # Recompute hash
            payload = f"{prev_hash}{ts}{detail}"
            expected_hash = hashlib.sha256(payload.encode()).hexdigest()
            if h != expected_hash:
                logger.error("Hash mismatch at ID %d: Recomputed %s, stored %s", row_id, expected_hash, h)
                return False
            
            current_prev = h
            
        return True
