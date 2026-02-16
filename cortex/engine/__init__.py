"""
CORTEX Engine — Package init.

Re-exports CortexEngine and Fact for backward compatibility.
The engine class is assembled from mixins for modularity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import sqlite_vec

from cortex.embeddings import LocalEmbedder
from cortex.schema import get_init_meta
from cortex.migrations import run_migrations
from cortex.graph import get_graph
from cortex.temporal import now_iso
from cortex.config import DEFAULT_DB_PATH

from cortex.engine.models import Fact, row_to_fact  # noqa: F401
from cortex.engine.store_mixin import StoreMixin
from cortex.engine.query_mixin import QueryMixin
from cortex.engine.consensus_mixin import ConsensusMixin

logger = logging.getLogger("cortex")


class CortexEngine(StoreMixin, QueryMixin, ConsensusMixin):
    """The Sovereign Ledger for AI Agents.

    Core engine providing:
    - Semantic vector search (sqlite-vec)
    - Temporal fact management (valid_from/valid_until)
    - Project-scoped isolation
    - Append-only transaction ledger

    Usage:
        engine = CortexEngine()
        engine.store("naroa-web", "Uses vanilla JS, no framework")
        results = engine.search("what framework does naroa use?")
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        auto_embed: bool = True,
    ):
        """Initialize or open CORTEX database."""
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_embed = auto_embed
        self._embedder: Optional[LocalEmbedder] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._vec_available = False

    # ─── Connection Management ────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create SQLite connection with vec0 extension."""
        if self._conn is not None:
            return self._conn
        self._conn = sqlite3.connect(
            str(self._db_path), timeout=30, check_same_thread=False
        )
        try:
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            if hasattr(self._conn, 'enable_load_extension'):
                self._conn.enable_load_extension(False)
            self._vec_available = True
        except (OSError, AttributeError) as e:
            logger.warning("sqlite-vec not available: %s. Vector search disabled.", e)
            self._vec_available = False
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def get_connection(self) -> sqlite3.Connection:
        """Public alias for _get_conn (backward compatibility)."""
        return self._get_conn()

    def _get_embedder(self) -> LocalEmbedder:
        """Get or create local embedder (lazy load)."""
        if self._embedder is None:
            self._embedder = LocalEmbedder()
        return self._embedder

    # ─── Database Initialization ──────────────────────────────────

    def init_db(self) -> None:
        """Initialize database schema using migrations."""
        from cortex.schema import ALL_SCHEMA, get_init_meta
        conn = self._get_conn()
        for stmt in ALL_SCHEMA:
            if "USING vec0" in stmt and not self._vec_available:
                continue
            conn.executescript(stmt)
        conn.commit()
        run_migrations(conn)
        for key, value in get_init_meta():
            conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()
        logger.info("CORTEX database initialized at %s", self._db_path)

    # ─── Graph ────────────────────────────────────────────────────

    def graph(self, project: Optional[str] = None, limit: int = 50) -> dict:
        """Get knowledge graph (entities and relationships)."""
        conn = self._get_conn()
        return get_graph(conn, project, limit)

    def query_entity(self, name: str, project: Optional[str] = None) -> Optional[dict]:
        """Query specific entity in the graph."""
        from cortex.graph import query_entity
        conn = self._get_conn()
        return query_entity(conn, name, project)

    def register_ghost(self, reference: str, context: str, project: str) -> int | str:
        """Register a ghost (unresolved reference) in the graph."""
        from cortex.graph import get_backend
        conn = self._get_conn()
        backend = get_backend(conn)
        return backend.upsert_ghost(reference, context, project, now_iso())

    def resolve_ghost(self, ghost_id: int | str, target_id: int | str, confidence: float = 1.0) -> bool:
        """Resolve a ghost to a concrete entity."""
        from cortex.graph import get_backend
        conn = self._get_conn()
        backend = get_backend(conn)
        return backend.resolve_ghost(ghost_id, target_id, confidence, now_iso())

    # ─── Transaction Ledger ───────────────────────────────────────

    def _log_transaction(
        self, conn: sqlite3.Connection, project: str, action: str, detail: dict,
    ) -> int:
        """Log an action to the immutable transaction ledger."""
        detail_json = json.dumps(detail, default=str)
        ts = now_iso()
        prev = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = prev[0] if prev else "GENESIS"
        hash_input = f"{prev_hash}:{project}:{action}:{detail_json}:{ts}"
        tx_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        cursor = conn.execute(
            "INSERT INTO transactions (project, action, detail, prev_hash, hash, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (project, action, detail_json, prev_hash, tx_hash, ts),
        )
        return cursor.lastrowid

    # ─── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _row_to_fact(row: tuple) -> Fact:
        """Convert a database row to a Fact object."""
        return row_to_fact(row)

    # ─── Lifecycle ────────────────────────────────────────────────

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return f"CortexEngine(db='{self._db_path}')"
