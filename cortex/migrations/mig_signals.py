# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Migration 019 — Signal Bus (L1 Consciousness Layer).

Adds the persistent signals table for cross-tool reactive communication.
"""

from __future__ import annotations

import sqlite3


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
