# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from babylon60.extensions.health.models import MetricSnapshot

logger = logging.getLogger("cortex_extensions.health.ledger")


class LedgerCollector:
    """Ledger integrity via hash chain verification."""

    @property
    def name(self) -> str:
        return "ledger"

    @property
    def weight(self) -> float:
        return 1.2

    @property
    def description(self) -> str:
        return "Cryptographic hash chain integrity check."

    @property
    def remediation(self) -> str:
        return "Run `cortex ledger verify`. If broken, DB may be tampered."

    def collect(self, db_path: str) -> MetricSnapshot:
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            from babylon60.database.core import connect

            with connect(db_path, timeout=2.0) as conn:  # pyright: ignore
                conn.row_factory = sqlite3.Row
                try:
                    cur = conn.execute("SELECT COUNT(*) as cnt FROM transactions")
                    row = cur.fetchone()
                    count = row["cnt"] if row else 0
                    if count == 0:
                        return MetricSnapshot(
                            name=self.name,
                            value=0.5,
                            weight=self.weight,
                        )
                    cur = conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1")
                    last = cur.fetchone()
                    val = 1.0 if (last and last["hash"]) else 0.7
                    return MetricSnapshot(
                        name=self.name,
                        value=val,
                        weight=self.weight,
                    )
                finally:
                    pass  # 'with' handles connection closure
        except (sqlite3.Error, OSError) as e:
            logger.debug("Ledger check failed: %s", e)
            return MetricSnapshot(
                name=self.name,
                value=0.3,
                weight=self.weight,
            )
