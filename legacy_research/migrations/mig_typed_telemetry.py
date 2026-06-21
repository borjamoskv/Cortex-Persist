# [C5-REAL] Exergy-Maximized
"""
Migration 030: Typed Epistemic Telemetry (Cortex v3)
"""

import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_030_typed_telemetry(conn: sqlite3.Connection):
    """Create structured schemas for Raw, Derived, and Narrative telemetry data."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cortex_raw_metrics (
            id              TEXT PRIMARY KEY,
            metric_name     TEXT NOT NULL,
            metric_value    REAL NOT NULL,
            labels          TEXT, -- JSON dictionary of labels
            timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cortex_derived_metrics (
            id              TEXT PRIMARY KEY,
            formula_id      TEXT NOT NULL,
            calculated_value REAL NOT NULL,
            inputs          TEXT NOT NULL, -- JSON list of raw_metric IDs used
            timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cortex_narrative_claims (
            id              TEXT PRIMARY KEY,
            label           TEXT NOT NULL,
            description     TEXT NOT NULL,
            evidence_roots  TEXT, -- JSON list of AST/git hashes
            timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    logger.info("Migration 030: Created typed epistemic telemetry schemas")
