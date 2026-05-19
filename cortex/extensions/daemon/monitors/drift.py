"""Autonomous Drift Monitor (El Topólogo).

Periodically samples L2 vector embeddings and checks topological health
against the persisted baseline. Fires DriftAlert if health drops below threshold.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

import numpy as np

from cortex.extensions.daemon.models import DriftAlert

logger = logging.getLogger("moskv-daemon")


class DriftMonitorDaemon:
    """Daemon monitor that checks L2 vector space topological stability.

    Runs at configurable intervals (default: every 6 hours) since drift
    is a slow phenomenon. Reads embeddings directly from sqlite-vec
    to avoid loading the full engine.
    """

    def __init__(
        self,
        vectors_db_path: Path | str,
        cortex_dir: Path | str | None = None,
        interval_seconds: int = 6 * 3600,  # 6 hours
        health_threshold: float = 0.5,
        model_name: str = "all-MiniLM-L6-v2",
        max_sample: int = 5000,
    ):
        self.vectors_db_path = Path(vectors_db_path)
        self.cortex_dir = Path(cortex_dir) if cortex_dir else self.vectors_db_path.parent.parent
        self.interval_seconds = interval_seconds
        self.health_threshold = health_threshold
        self.model_name = model_name
        self.max_sample = max_sample
        self._last_run: float = 0

    def check(self) -> list[DriftAlert]:
        """Run drift health check if interval elapsed."""
        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        if not self.vectors_db_path.exists():
            return []

        self._last_run = now

        try:
            return self._run_check()
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as e:
            logger.error("Drift monitor failed: %s", e)
            return []

    def _run_check(self) -> list[DriftAlert]:
        """Execute the actual drift check against persisted baseline."""
        from cortex.memory.drift import DriftMonitor, model_hash_from_name

        model_hash = model_hash_from_name(self.model_name)
        signature_dir = self.cortex_dir / "drift"

        monitor = DriftMonitor(
            model_hash=model_hash,
            signature_dir=signature_dir,
        )

        # Load baseline
        baseline = monitor.load_baseline()

        # Read embeddings from sqlite-vec
        embeddings = self._read_embeddings()
        if embeddings is None or embeddings.shape[0] < 10:
            return []

        # If no baseline exists, create one silently
        if baseline is None:
            monitor.checkpoint(embeddings)
            logger.info("DriftMonitor: Created initial baseline (n=%d)", embeddings.shape[0])
            return []

        # Compute health
        result = monitor.health(embeddings, baseline)
        health = result["topological_health"]

        if health < self.health_threshold:
            alert = DriftAlert(
                health=health,
                centroid_drift=result["centroid_drift"],
                spectral_ratio=result["spectral_ratio"],
                n_vectors=embeddings.shape[0],
                message=(f"Vector space drift detected: health={health:.2f} ({result['detail']})"),
            )
            logger.warning("DriftMonitor: %s", alert.message)
            return [alert]

        logger.info("DriftMonitor: Healthy (%.2f) — %s", health, result["detail"])
        return []

    def _read_embeddings(self) -> np.ndarray | None:
        """Read embedding vectors from the sqlite-vec store.

        Samples up to max_sample vectors to keep computation bounded.
        """
        try:
            import sqlite_vec
        except ImportError:
            logger.warning("DriftMonitor: sqlite_vec not available, skipping")
            return None

        try:
            from cortex.database.core import connect as db_connect

            conn = db_connect(str(self.vectors_db_path), timeout=10)
            conn.execute("PRAGMA busy_timeout=10000")
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)

            # Check table exists
            cursor = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vec_facts'"
            )
            if not cursor.fetchone():
                conn.close()
                return None

            # Count vectors
            cursor = conn.execute("SELECT COUNT(*) FROM vec_facts")
            total = cursor.fetchone()[0]

            if total == 0:
                conn.close()
                return None

            # Read embeddings (sample if too many)
            if total <= self.max_sample:
                cursor = conn.execute("SELECT embedding FROM vec_facts")
            else:
                # Random sample via rowid
                cursor = conn.execute(
                    "SELECT embedding FROM vec_facts ORDER BY RANDOM() LIMIT ?",
                    (self.max_sample,),
                )

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return None

            # Convert binary blobs to numpy array
            vectors = [np.frombuffer(row[0], dtype=np.float32) for row in rows]
            return np.vstack(vectors)

        except (sqlite3.Error, OSError) as e:
            logger.warning("DriftMonitor: Failed to read embeddings: %s", e)
            return None
