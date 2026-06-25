# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Migration 019 - Signal Bus (L1 Consciousness Layer).

Adds the persistent signals table for cross-tool reactive communication.
"""

from __future__ import annotations

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


def _migration_019_signal_bus(conn: sqlite3.Connection) -> None:
    """Create the signals table and indexes."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            payload     TEXT NOT NULL DEFAULT '{}',
            source      TEXT NOT NULL,
            project     TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            consumed_by TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
        CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
        CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
        CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
    """)
