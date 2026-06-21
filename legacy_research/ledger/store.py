# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class LedgerStoreError(RuntimeError):
    """Base exception for ledger store errors."""


class LedgerStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        from cortex.database.core import connect

        return connect(self.db_path, row_factory=sqlite3.Row)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            if getattr(exc, "preserve_ledger_error", False):
                raise
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
                    mldsa_signature TEXT,
                    mldsa_public_key TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );

                CREATE TABLE IF NOT EXISTS enrichment_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    event_id TEXT,
                    fact_id INTEGER,
                    job_type TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    priority INTEGER DEFAULT 0,
                    next_attempt_ts TEXT,
                    next_attempt_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    FOREIGN KEY(event_id) REFERENCES ledger_events(event_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_ledger_events_ts ON ledger_events(ts);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_hash ON ledger_events(hash);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_semantic_status
                    ON ledger_events(semantic_status);

                CREATE TABLE IF NOT EXISTS ledger_enrichment_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    event_id TEXT,
                    fact_id INTEGER,
                    job_type TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    priority INTEGER DEFAULT 0,
                    next_attempt_ts TEXT,
                    next_attempt_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    FOREIGN KEY(event_id) REFERENCES ledger_events(event_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ledger_replay_admissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    ledger_event_id TEXT NOT NULL,
                    actor_key_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                """
            )
            self._ensure_compat_columns(conn, "enrichment_jobs")
            self._ensure_compat_columns(conn, "ledger_enrichment_jobs")
            self._ensure_checkpoint_mldsa_columns(conn)
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_ledger_events_ts ON ledger_events(ts);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_hash ON ledger_events(hash);
                CREATE INDEX IF NOT EXISTS idx_ledger_events_semantic_status
                    ON ledger_events(semantic_status);
                CREATE INDEX IF NOT EXISTS idx_ledger_enrichment_jobs_status_next_attempt_compat
                    ON ledger_enrichment_jobs(status, COALESCE(next_attempt_ts, next_attempt_at));
                CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_replay_tenant_event_id
                    ON ledger_replay_admissions(tenant_id, event_id);
                CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_replay_tenant_nonce
                    ON ledger_replay_admissions(tenant_id, nonce);
                CREATE INDEX IF NOT EXISTS idx_ledger_replay_tenant_accepted
                    ON ledger_replay_admissions(tenant_id, accepted_at);

                CREATE TRIGGER IF NOT EXISTS enrichment_jobs_ledger_insert
                AFTER INSERT ON enrichment_jobs
                BEGIN
                    INSERT OR REPLACE INTO ledger_enrichment_jobs (
                        id,
                        job_id,
                        event_id,
                        fact_id,
                        job_type,
                        status,
                        attempts,
                        priority,
                        next_attempt_ts,
                        next_attempt_at,
                        last_error,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        NEW.id,
                        NEW.job_id,
                        NEW.event_id,
                        NEW.fact_id,
                        NEW.job_type,
                        NEW.status,
                        NEW.attempts,
                        NEW.priority,
                        NEW.next_attempt_ts,
                        NEW.next_attempt_at,
                        NEW.last_error,
                        NEW.created_at,
                        NEW.updated_at
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS enrichment_jobs_ledger_update
                AFTER UPDATE ON enrichment_jobs
                BEGIN
                    INSERT OR REPLACE INTO ledger_enrichment_jobs (
                        id,
                        job_id,
                        event_id,
                        fact_id,
                        job_type,
                        status,
                        attempts,
                        priority,
                        next_attempt_ts,
                        next_attempt_at,
                        last_error,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        NEW.id,
                        NEW.job_id,
                        NEW.event_id,
                        NEW.fact_id,
                        NEW.job_type,
                        NEW.status,
                        NEW.attempts,
                        NEW.priority,
                        NEW.next_attempt_ts,
                        NEW.next_attempt_at,
                        NEW.last_error,
                        NEW.created_at,
                        NEW.updated_at
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS enrichment_jobs_ledger_delete
                AFTER DELETE ON enrichment_jobs
                BEGIN
                    DELETE FROM ledger_enrichment_jobs WHERE job_id = OLD.job_id;
                END;
                """
            )

    def _ensure_compat_columns(self, conn: sqlite3.Connection, table_name: str) -> None:
        """Backfill compatibility columns for legacy ledger job tables."""
        from cortex.utils.sql_identifiers import validate_sql_identifier

        validate_sql_identifier(table_name)
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        for column in ("next_attempt_ts", "next_attempt_at"):
            if column not in existing:
                validate_sql_identifier(column)
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} TEXT")

    def _ensure_checkpoint_mldsa_columns(self, conn: sqlite3.Connection) -> None:
        """Backfill compatibility columns for MLDSA post-quantum checkpoint signatures."""
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(ledger_checkpoints)").fetchall()
        }
        for column in ("mldsa_signature", "mldsa_public_key"):
            if column not in existing:
                conn.execute(f"ALTER TABLE ledger_checkpoints ADD COLUMN {column} TEXT")
