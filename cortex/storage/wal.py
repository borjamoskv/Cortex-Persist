import sqlite3
import json
import time
import threading
from pathlib import Path
from typing import Optional
from cortex.database.core import connect

WAL_PATH = "cortex/data/batch_wal.db"
BATCH_WINDOW_MS = 50


class WriteAheadLog:
    """
    Every async event is materialized in the WAL (status='pending')
    BEFORE entering the in-memory batch queue.

    On crash recovery, unsealed events are replayed.
    """

    def __init__(self, db_path: str = WAL_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_wal (
                    event_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    received_at_epoch_ms INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'sealed', 'rejected')),
                    event_hash TEXT,
                    previous_hash TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wal_status
                ON batch_wal(status)
            """)
            conn.commit()
            conn.close()

    def write_pending(self, event_id: str, payload: dict, previous_hash: str = None) -> str:
        """Atomic write before memory queue insertion. Returns the event_hash."""
        import hashlib
        payload_str = json.dumps(payload)
        now_ms = int(time.time() * 1000)
        
        # Calculate event hash for Rust validation
        hash_input = f"{event_id}:{payload_str}:{now_ms}:{previous_hash or 'genesis'}"
        event_hash = hashlib.sha3_256(hash_input.encode()).hexdigest()
        
        with self._lock:
            conn = connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO batch_wal (event_id, payload, received_at_epoch_ms, status, event_hash, previous_hash) "
                "VALUES (?, ?, ?, 'pending', ?, ?)",
                (event_id, payload_str, now_ms, event_hash, previous_hash)
            )
            conn.commit()
            conn.close()
        
        return event_hash

    def seal_batch(self, event_ids: list[str]) -> None:
        """Mark as sealed after Merkle root is computed."""
        with self._lock:
            conn = connect(self.db_path)
            placeholders = ','.join('?' * len(event_ids))
            conn.execute(
                f"UPDATE batch_wal SET status = 'sealed' "
                f"WHERE event_id IN ({placeholders})",
                event_ids
            )
            conn.commit()
            conn.close()

    def recover_unsealed(self) -> list[dict]:
        """
        Called during bootstrap watchdog.
        Returns all pending events that were never sealed.
        """
        with self._lock:
            conn = connect(self.db_path)
            cursor = conn.execute(
                "SELECT payload FROM batch_wal WHERE status = 'pending'"
            )
            rows = [json.loads(row[0]) for row in cursor.fetchall()]
            conn.close()
            return rows

    def mark_rejected(self, event_ids: list[str]) -> None:
        """Events that failed ZK validation or consensus."""
        with self._lock:
            conn = connect(self.db_path)
            placeholders = ','.join('?' * len(event_ids))
            conn.execute(
                f"UPDATE batch_wal SET status = 'rejected' "
                f"WHERE event_id IN ({placeholders})",
                event_ids
            )
            conn.commit()
            conn.close()
