# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
"""CORTEX LLM Result Cache - Persistent Semantic Deduplication.

Prevents redundant expensive API calls during audits, tests, or iterative runs.
Uses SQLite WAL for zero-latency cross-process synchronization (Ω₂).
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import tempfile
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class ResultCache:
    """Persistent LLM response cache on SQLite WAL."""

    def __init__(self, db_path: str = "~/.cortex/llm_cache.db"):
        self.db_path = Path(db_path).expanduser()
        self._available = True
        try:
            self._init_db()
        except (OSError, sqlite3.OperationalError) as exc:
            self._available = False
            logger.warning("LLM Cache [DISABLED] -> %s", exc)

    def _init_db(self) -> None:
        candidates = [self.db_path]
        fallback = Path(tempfile.gettempdir()) / "cortex_llm_cache.db"
        if fallback not in candidates:
            candidates.append(fallback)

        last_error: sqlite3.OperationalError | OSError | None = None
        for candidate in candidates:
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                with _db(candidate) as conn:
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
                if candidate != self.db_path:
                    logger.warning(
                        "LLM cache DB unavailable at %s; falling back to %s",
                        self.db_path,
                        candidate,
                    )
                    self.db_path = candidate
                return
            except (OSError, sqlite3.OperationalError) as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

    def _make_hash(self, prompt: dict[str, Any]) -> str:
        """Deterministic SHA256 of the prompt components."""
        # Sort keys to ensure stability
        canonical = json.dumps(prompt, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def get(self, prompt: dict[str, Any]) -> str | None:
        """Retrieve cached response if it exists and hasn't expired."""
        if not self._available:
            return None
        h = self._make_hash(prompt)
        now = time.monotonic()
        try:
            with _db(self.db_path) as conn:
                row = conn.execute(
                    "SELECT response FROM results WHERE hash = ? AND expires_at > ?", (h, now)
                ).fetchone()
                if row:
                    logger.debug("LLM Cache [HIT] -> %s...", h[:8])
                    return row[0]
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)
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
        if not self._available:
            return
        h = self._make_hash(prompt)
        now = time.monotonic()
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
        if not self._available:
            return
        with _db(self.db_path, exclusive=True) as conn:
            conn.execute("DELETE FROM results")
        logger.warning("LLM Cache [PURGED].")

    def cleanup(self) -> int:
        """Remove expired entries. Returns eviction count."""
        if not self._available:
            return 0
        now = time.monotonic()
        with _db(self.db_path, exclusive=True) as conn:
            cursor = conn.execute("DELETE FROM results WHERE expires_at <= ?", (now,))
            return cursor.get_count() if hasattr(cursor, "get_count") else cursor.rowcount  # pyright: ignore
