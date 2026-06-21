# [C5-REAL] Exergy-Maximized
"""Migration for Temporal Knowledge Graph.

Adds decay_half_life to facts.
Adds confidence and agent_id to causal_edges.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations.mig_temporal_kg")


def _migration_027_temporal_kg(conn: sqlite3.Connection) -> None:
    """Add temporal graph columns to facts and causal_edges."""
    # Facts decay_half_life
    try:
        conn.execute("ALTER TABLE facts ADD COLUMN decay_half_life REAL DEFAULT 30.0")
        logger.info("Added decay_half_life to facts")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise
        logger.debug("Column decay_half_life already exists on facts")

    # Causal_edges confidence
    try:
        conn.execute("ALTER TABLE causal_edges ADD COLUMN confidence REAL DEFAULT 1.0")
        logger.info("Added confidence to causal_edges")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise
        logger.debug("Column confidence already exists on causal_edges")

    # Causal_edges agent_id
    try:
        conn.execute("ALTER TABLE causal_edges ADD COLUMN agent_id TEXT")
        logger.info("Added agent_id to causal_edges")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise
        logger.debug("Column agent_id already exists on causal_edges")
