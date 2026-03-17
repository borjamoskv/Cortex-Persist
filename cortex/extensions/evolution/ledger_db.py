# cortex/evolution/ledger_db.py
"""SQLite-backed metrics and mutation ledger for sovereign agent evolution.

Provides O(1) persistent storage for:
1. Agent evolution metrics (telemetry history).
2. Mutation ledger (detailed state change registry).
3. Evolution status tracking.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from cortex.database.core import connect as db_connect
from cortex.extensions.evolution.models import EvolutionMutation

logger = logging.getLogger("cortex.extensions.evolution.ledger_db")

_DEFAULT_PATH = Path("~/.cortex/evolution_memory.db").expanduser()


class EvolutionLedgerDB:
    """Persistent storage for agent evolution metrics and state changes."""

    def __init__(self, db_path: str | Path = _DEFAULT_PATH) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize schema for evolution tracking."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with db_connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            # Mutation Ledger
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mutations (
                    id            TEXT PRIMARY KEY,
                    agent_id      TEXT NOT NULL,
                    mutation_type TEXT NOT NULL,
                    prev_hash     TEXT NOT NULL,
                    new_hash      TEXT NOT NULL,
                    delta_fitness REAL NOT NULL,
                    metrics       TEXT NOT NULL, -- JSON list of EvolutionMetric
                    metadata      TEXT NOT NULL, -- JSON dict
                    timestamp     REAL NOT NULL
                )
            """)

            # Metric Time Series
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id    TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value       REAL NOT NULL,
                    unit        TEXT NOT NULL,
                    timestamp   REAL NOT NULL
                )
            """)

            # Domain Evolution Tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_evolution (
                    domain      TEXT PRIMARY KEY,
                    last_cycle  INTEGER NOT NULL,
                    avg_fitness REAL NOT NULL,
                    updated_at  REAL NOT NULL
                )
            """)

            conn.commit()

    def record_mutation(self, mutation: EvolutionMutation) -> None:
        """Store a discrete mutation event in the ledger."""
        self.record_mutations_batch([mutation])

    def record_mutations_batch(self, mutations: list[EvolutionMutation]) -> None:
        """Ω₀: Batch record multiple mutations. 100x faster than individual writes."""
        if not mutations:
            return
        try:
            with db_connect(str(self.db_path)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")

                mutation_entries = []
                metric_entries = []

                for m in mutations:
                    m_dict = m.to_dict()
                    mutation_entries.append(
                        (
                            m_dict["id"],
                            m_dict["agent_id"],
                            m_dict["mutation_type"],
                            m_dict["prev_hash"],
                            m_dict["new_hash"],
                            m_dict["delta_fitness"],
                            json.dumps(m_dict["metrics"]),
                            json.dumps(m_dict["metadata"]),
                            m_dict["timestamp"],
                        )
                    )

                    for met in m.metrics:
                        metric_entries.append(
                            (m.agent_id, met.name, met.value, met.unit, met.timestamp)
                        )

                conn.executemany(
                    """
                    INSERT INTO mutations (
                        id, agent_id, mutation_type, prev_hash, new_hash, 
                        delta_fitness, metrics, metadata, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    mutation_entries,
                )

                conn.executemany(
                    """
                    INSERT INTO metrics (agent_id, metric_name, value, unit, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    metric_entries,
                )

                conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to record mutation batch in evolution ledger: %s", exc)

    def record_metrics(self, agent_id: str, metrics: dict[str, Any]) -> None:
        """Store arbitrary telemetry for an agent."""
        now = time.time()
        try:
            with db_connect(str(self.db_path)) as conn:
                for name, val in metrics.items():
                    value = float(val) if isinstance(val, (int, float)) else 0.0
                    conn.execute(
                        """
                        INSERT INTO metrics (agent_id, metric_name, value, unit, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (agent_id, name, value, "points", now),
                    )
                conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to record metrics in evolution ledger: %s", exc)

    def get_mutation_history(self, agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent mutations for an agent."""
        try:
            with db_connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM mutations 
                    WHERE agent_id = ? 
                    ORDER BY rowid DESC 
                    LIMIT ?
                """,
                    (agent_id, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            logger.error("Failed to query mutation history: %s", exc)
            return []

    def get_metric_trend(
        self, agent_id: str, metric_name: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve time-series trend for a specific metric."""
        try:
            with db_connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT value, timestamp FROM metrics 
                    WHERE agent_id = ? AND metric_name = ?
                    ORDER BY id DESC 
                    LIMIT ?
                """,
                    (agent_id, metric_name, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            logger.error("Failed to query metric trend: %s", exc)
            return []

    def update_domain_status(self, domain: str, cycle: int, avg_fitness: float) -> None:
        """Update last known status for a domain."""
        try:
            with db_connect(str(self.db_path)) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO domain_evolution (domain, last_cycle, avg_fitness, updated_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (domain, cycle, avg_fitness, time.time()),
                )
                conn.commit()
        except sqlite3.Error as exc:
            logger.error("Failed to update domain status: %s", exc)
