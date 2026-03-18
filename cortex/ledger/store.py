from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


from typing import Union


class LedgerStoreError(RuntimeError):
    pass


class LedgerStore:
    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise LedgerStoreError(str(exc)) from exc
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.tx() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ledger_events (
                    event_id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT,
                    hash TEXT,
                    semantic_status TEXT NOT NULL DEFAULT 'pending',
                    semantic_error TEXT,
                    correlation_id TEXT,
                    trace_id TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );

                CREATE TABLE IF NOT EXISTS ledger_checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_hash TEXT NOT NULL,
                    start_event_id TEXT NOT NULL,
                    end_event_id TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );

                CREATE TABLE IF NOT EXISTS ledger_enrichment_jobs (
                    job_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_ts TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    FOREIGN KEY(event_id) REFERENCES ledger_events(event_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_ledger_events_ts ON ledger_events(ts);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_hash ON ledger_events(hash);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_semantic_status ON ledger_events(semantic_status);
                CREATE INDEX IF NOT EXISTS idx_ledger_enrichment_jobs_status_next_attempt
                    ON ledger_enrichment_jobs(status, next_attempt_ts);
                """
            )
