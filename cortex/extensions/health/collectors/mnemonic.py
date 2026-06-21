# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from cortex.extensions.health.models import HealthThresholds, MetricSnapshot


class EntropyCollector:
    """Entropy from fact type diversity + volume."""

    @property
    def name(self) -> str:
        return "entropy"

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def description(self) -> str:
        return "Type diversity and information volume (Shannon)."

    @property
    def remediation(self) -> str:
        return "Inject more varied context via ADK or Web tools."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.5,
                weight=self.weight,
            )
        try:
            from cortex.database.core import connect

            with connect(db_path, timeout=2.0) as conn:  # pyright: ignore
                try:
                    cur = conn.execute(
                        "SELECT COUNT(DISTINCT fact_type) as types, "
                        "COUNT(*) as total FROM facts "
                        "WHERE valid_until IS NULL"
                    )
                    row = cur.fetchone()
                    if not row or row[1] == 0:
                        return MetricSnapshot(
                            name=self.name,
                            value=0.5,
                            weight=self.weight,
                        )
                    type_score = min(1.0, row[0] / t.type_diversity)
                    vol_score = min(1.0, row[1] / t.fact_target)
                    combined = type_score * 0.6 + vol_score * 0.4
                    return MetricSnapshot(
                        name=self.name,
                        value=combined,
                        weight=self.weight,
                    )
                finally:
                    pass
        except (sqlite3.Error, OSError):
            return MetricSnapshot(
                name=self.name,
                value=0.5,
                weight=self.weight,
            )


class FactCountCollector:
    """Active fact volume measurement."""

    @property
    def name(self) -> str:
        return "facts"

    @property
    def weight(self) -> float:
        return 0.8

    @property
    def description(self) -> str:
        return "Total volume of active mnemonic facts."

    @property
    def remediation(self) -> str:
        return "Store more facts to build agent context, or compact if too high."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            from cortex.database.core import connect

            with connect(db_path, timeout=2.0) as conn:  # pyright: ignore
                try:
                    cur = conn.execute("SELECT COUNT(*) FROM facts WHERE valid_until IS NULL")
                    row = cur.fetchone()
                    count = row[0] if row else 0
                    val = min(1.0, count / t.fact_target)
                    return MetricSnapshot(
                        name=self.name,
                        value=val,
                        weight=self.weight,
                    )
                finally:
                    pass
        except (sqlite3.Error, OSError):
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )


class SnapshotAgeCollector:
    """Age of the latest context snapshot."""

    @property
    def name(self) -> str:
        return "snapshot"

    @property
    def weight(self) -> float:
        return 0.7

    @property
    def description(self) -> str:
        return "Age of latest context snapshot."

    @property
    def remediation(self) -> str:
        return "Update snapshot via `cortex context snapshot`."

    def collect(self, db_path: str) -> MetricSnapshot:
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(name=self.name, value=0.5, weight=self.weight)
        try:
            from cortex.database.core import connect

            with connect(db_path, timeout=2.0) as conn:  # pyright: ignore
                try:
                    cur = conn.execute("SELECT MAX(created_at) FROM context_snapshots")
                    row = cur.fetchone()
                    if not row or not row[0]:
                        return MetricSnapshot(
                            name=self.name,
                            value=0.3,
                            weight=self.weight,
                            description="No snapshots found",
                        )
                    from datetime import datetime, timezone

                    ts = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    age_hours = (
                        datetime.fromtimestamp(time.time(), tz=timezone.utc) - ts
                    ).total_seconds() / 3600
                    if age_hours < 1:
                        val = 1.0
                    elif age_hours < 6:
                        val = 0.8
                    elif age_hours < 24:
                        val = 0.5
                    else:
                        val = 0.3
                    return MetricSnapshot(
                        name=self.name,
                        value=val,
                        weight=self.weight,
                        description=f"Age: {age_hours:.0f}h ({age_hours * 60:.0f} min)",
                    )
                finally:
                    pass
        except (sqlite3.Error, OSError, ValueError):
            return MetricSnapshot(name=self.name, value=0.5, weight=self.weight)
