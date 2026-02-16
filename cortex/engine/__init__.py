"""CORTEX Engine — Package init."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import sqlite_vec

from cortex.config import DEFAULT_DB_PATH
from cortex.embeddings import LocalEmbedder
from cortex.graph import get_graph
from cortex.migrations import run_migrations
from cortex.schema import get_init_meta
from cortex.temporal import now_iso

from cortex.engine.models import Fact, row_to_fact
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.consensus_mixin import ConsensusMixin

logger = logging.getLogger("cortex")


class CortexEngine(StoreMixin, QueryMixin, ConsensusMixin):
    """The Sovereign Ledger for AI Agents."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._embedder: Optional[LocalEmbedder] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._vec_available = False
        self._ledger = None  # Wave 5: ImmutableLedger (lazy init)

    # ─── Connection ───────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        self._conn = sqlite3.connect(
            str(self._db_path), timeout=30, check_same_thread=False
        )

        try:
            if hasattr(self._conn, "enable_load_extension"):
                self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            if hasattr(self._conn, "enable_load_extension"):
                self._conn.enable_load_extension(False)
            self._vec_available = True
        except (OSError, AttributeError):
            self._vec_available = False

        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def get_connection(self) -> sqlite3.Connection:
        """Public alias for backward compatibility."""
        return self._get_conn()

    def _get_embedder(self) -> LocalEmbedder:
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Schema ───────────────────────────────────────────────────

    def init_db(self) -> None:
        """Initialize database schema. Safe to call multiple times."""
        from cortex.schema import ALL_SCHEMA
        from cortex.ledger import ImmutableLedger

        conn = self._get_conn()

        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()

        run_migrations(conn)

        for k, v in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (k, v),
            )
        conn.commit()

        # Wave 5: Initialize Immutable Ledger
        self._ledger = ImmutableLedger(conn)
        logger.info("CORTEX database initialized at %s", self._db_path)

    # ─── Transaction Ledger ───────────────────────────────────────

    def _log_transaction(self, conn, project, action, detail) -> int:
        dj = json.dumps(detail, default=str)
        ts = now_iso()
        prev = conn.execute(
            "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        ph = prev[0] if prev else "GENESIS"
        th = hashlib.sha256(
            f"{ph}:{project}:{action}:{dj}:{ts}".encode()
        ).hexdigest()
        c = conn.execute(
            "INSERT INTO transactions "
            "(project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid

        # Wave 5: Auto-checkpoint after threshold
        if self._ledger:
            try:
                self._ledger.create_checkpoint()
            except Exception as e:
                logger.warning("Auto-checkpoint failed: %s", e)

        return tx_id

    def verify_ledger(self) -> dict:
        """Verify ledger integrity (hash chain + Merkle checkpoints)."""
        if not self._ledger:
            from cortex.ledger import ImmutableLedger
            self._ledger = ImmutableLedger(self._get_conn())
        return self._ledger.verify_integrity()

    # ─── Helpers ──────────────────────────────────────────────────

    def export_snapshot(self, out_path: str | Path) -> str:
        from cortex.sync.snapshot import export_snapshot
        return export_snapshot(self, out_path)

    @staticmethod
    def _row_to_fact(row) -> Fact:
        return row_to_fact(row)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
