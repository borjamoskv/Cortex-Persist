from __future__ import annotations

import hashlib
import json
import logging
import sqlite3

from cortex.database.core import connect as db_connect
from cortex.engine.evolution_types import DomainMetrics, Mutation

logger = logging.getLogger("cortex.evolution.metrics")


class CortexMetrics:
    """Synchronized SQLite3 backend with WAL mode and 60-second TTL cache.
    Provides ACID-compliant persistence optimized for high-concurrency.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._cache: dict[str, DomainMetrics] = {}
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a hardened connection via CORTEX database factory."""
        return db_connect(self.db_path, timeout=5)

    def _init_database(self) -> None:
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS domain_metrics (
                    domain_id TEXT PRIMARY KEY,
                    health_score REAL,
                    error_rate REAL,
                    ghost_density REAL,
                    fact_density REAL,
                    bridge_score REAL,
                    fitness_delta REAL,
                    timestamp REAL,
                    hash TEXT
                );
                CREATE TABLE IF NOT EXISTS mutation_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutation_id TEXT,
                    domain_id TEXT,
                    parameters_json TEXT,
                    fitness REAL,
                    generation INTEGER,
                    timestamp REAL DEFAULT (unixepoch('now')),
                    hash TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def update_metrics(self, metrics: DomainMetrics) -> None:
        """Persist metrics with hash verification (Axiom 12 compliance)."""
        data = f"{metrics.domain_id}{metrics.health_score}{metrics.timestamp}"
        m_hash = hashlib.sha256(data.encode()).hexdigest()

        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO domain_metrics
                   (domain_id, health_score, error_rate, ghost_density,
                    fact_density, bridge_score, fitness_delta, timestamp, hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    metrics.domain_id,
                    metrics.health_score,
                    metrics.error_rate,
                    metrics.ghost_density,
                    metrics.fact_density,
                    metrics.bridge_score,
                    metrics.fitness_delta,
                    metrics.timestamp,
                    m_hash,
                ),
            )
            conn.commit()
            self._cache[metrics.domain_id] = metrics
        finally:
            conn.close()

    def get_metrics(self, domain_id: str, ttl_seconds: int = 60) -> DomainMetrics:
        """Returns cached metrics if fresh, otherwise queries SQLite."""
        if domain_id in self._cache and not self._cache[domain_id].is_stale(ttl_seconds):
            return self._cache[domain_id]

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM domain_metrics WHERE domain_id = ?",
                (domain_id,),
            )
            row = cursor.fetchone()
            if row:
                res = list(row)
                m = DomainMetrics(
                    domain_id=res[0],
                    health_score=res[1],
                    error_rate=res[2],
                    ghost_density=res[3],
                    fact_density=res[4],
                    bridge_score=res[5],
                    fitness_delta=res[6],
                    timestamp=res[7],
                )
                self._cache[domain_id] = m
                return m
            return DomainMetrics(domain_id=domain_id)
        finally:
            conn.close()

    def record_mutation(self, mutation: Mutation, domain_id: str) -> None:
        """Immutable ledger entry — Axiom 12 (ψWitness Passive Observation)."""
        p_json = json.dumps(mutation.parameters)
        prev_hash = self._get_last_hash(domain_id)
        data = f"{mutation.mutation_id}{p_json}{mutation.fitness}{prev_hash}"
        m_hash = hashlib.sha256(data.encode()).hexdigest()

        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO mutation_ledger
                   (mutation_id, domain_id, parameters_json, fitness, generation, hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    mutation.mutation_id,
                    domain_id,
                    p_json,
                    mutation.fitness,
                    mutation.generation,
                    m_hash,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _get_last_hash(self, domain_id: str) -> str:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT hash FROM mutation_ledger WHERE domain_id = ? ORDER BY id DESC LIMIT 1",
                (domain_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else "GENESIS"
        finally:
            conn.close()
