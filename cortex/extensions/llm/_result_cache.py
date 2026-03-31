# This file is part of CORTEX. Apache-2.0.
"""CORTEX LLM Result Cache — Persistent Semantic Deduplication.

Prevents redundant expensive API calls during audits, tests, or iterative runs.
Uses SQLite WAL for zero-latency cross-process synchronization (Ω₂).
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect

logger = logging.getLogger("cortex.extensions.llm.cache")

# Default cache TTL: 24 hours
_DEFAULT_TTL: int = 86400


@contextmanager
def _db(path: Path, exclusive: bool = False) -> Generator[sqlite3.Connection, None, None]:
    """Sovereign context manager for SQLite via CORTEX factory."""
    conn = db_connect(str(path), timeout=5)
    try:
        if exclusive:
            conn.execute("BEGIN EXCLUSIVE")
        yield conn
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise
    finally:
        conn.close()


class ResultCache:
    """Persistent LLM response cache on SQLite WAL."""

    def __init__(self, db_path: str = "~/.cortex/llm_cache.db"):
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with _db(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    hash         TEXT PRIMARY KEY,
                    response     TEXT NOT NULL,
                    expires_at   REAL NOT NULL,
                    created_at   REAL NOT NULL,
                    provider     TEXT,
                    model        TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON results(expires_at)")

    def _make_hash(self, prompt: dict[str, Any]) -> str:
        """Deterministic SHA256 of the prompt components."""
        # Sort keys to ensure stability
        canonical = json.dumps(prompt, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, prompt: dict[str, Any]) -> str | None:
        """Retrieve cached response if it exists and hasn't expired."""
        h = self._make_hash(prompt)
        now = time.time()
        try:
            with _db(self.db_path) as conn:
                row = conn.execute(
                    "SELECT response FROM results WHERE hash = ? AND expires_at > ?", (h, now)
                ).fetchone()
                if row:
                    logger.debug("LLM Cache [HIT] -> %s...", h[:8])
                    return row[0]
        except sqlite3.OperationalError:
            pass
        return None

    def set(
        self,
        prompt: dict[str, Any],
        response: str,
        provider: str | None = None,
        model: str | None = None,
        ttl: int = _DEFAULT_TTL,
    ) -> None:
        """Cache an LLM response."""
        h = self._make_hash(prompt)
        now = time.time()
        expires = now + ttl
        try:
            with _db(self.db_path, exclusive=True) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO results 
                    (hash, response, expires_at, created_at, provider, model)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (h, response, expires, now, provider, model),
                )
            logger.debug("LLM Cache [SET] -> %s", h[:8])
        except sqlite3.OperationalError:
            logger.warning("LLM Cache [FAIL] -> DB busy, skipping cache set.")

    def clear(self) -> None:
        """Evict all cached results."""
        with _db(self.db_path, exclusive=True) as conn:
            conn.execute("DELETE FROM results")
        logger.warning("LLM Cache [PURGED].")

    def cleanup(self) -> int:
        """Remove expired entries. Returns eviction count."""
        now = time.time()
        with _db(self.db_path, exclusive=True) as conn:
            cursor = conn.execute("DELETE FROM results WHERE expires_at <= ?", (now,))
            return cursor.get_count() if hasattr(cursor, "get_count") else cursor.rowcount  # pyright: ignore
