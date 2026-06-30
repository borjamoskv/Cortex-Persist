# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import os
from pathlib import Path

from babylon60.extensions.health.models import HealthThresholds, MetricSnapshot


class DbCollector:
    """Database existence and size check."""

    @property
    def name(self) -> str:
        return "db"

    @property
    def weight(self) -> float:
        return 1.5

    @property
    def description(self) -> str:
        return "Core SQLite database file size and health."

    @property
    def remediation(self) -> str:
        return "Run `cortex gc` or consider archiving old facts."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path or not Path(db_path).exists():
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        try:
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
        except OSError:
            return MetricSnapshot(
                name=self.name,
                value=0.0,
                weight=self.weight,
            )
        if size_mb < t.db_warn_mb:
            val = 1.0
        elif size_mb < t.db_crit_mb:
            val = 0.8
        else:
            val = 0.5
        return MetricSnapshot(
            name=self.name,
            value=val,
            weight=self.weight,
        )


class WalCollector:
    """WAL file pressure check."""

    @property
    def name(self) -> str:
        return "wal"

    @property
    def weight(self) -> float:
        return 0.6

    @property
    def description(self) -> str:
        return "Write-Ahead Log size (checkpoint pressure)."

    @property
    def remediation(self) -> str:
        return "Restart daemon or force SQLite PRAGMA wal_checkpoint."

    def collect(self, db_path: str) -> MetricSnapshot:
        t = HealthThresholds()
        if not db_path:
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )
        wal_path = Path(f"{db_path}-wal")
        if not wal_path.exists():
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )
        try:
            wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
            if wal_mb < t.wal_warn_mb:
                val = 1.0
            elif wal_mb < t.wal_crit_mb:
                val = 0.5
            else:
                val = 0.2
            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
            )
        except OSError:
            return MetricSnapshot(
                name=self.name,
                value=1.0,
                weight=self.weight,
            )


class DiskSpaceCollector:
    """Free disk space on the volume hosting the DB."""

    @property
    def name(self) -> str:
        return "disk"

    @property
    def weight(self) -> float:
        return 1.4

    @property
    def description(self) -> str:
        return "Free disk space on DB volume."

    @property
    def remediation(self) -> str:
        return "Free disk space or move DB to a larger volume."

    def collect(self, db_path: str) -> MetricSnapshot:
        import shutil

        target = db_path if db_path and Path(db_path).exists() else "/"
        try:
            usage = shutil.disk_usage(Path(target).parent)
            free_gb = usage.free / (1024**3)
            if free_gb > 50:
                val = 1.0
            elif free_gb > 20:
                val = 0.8
            elif free_gb > 5:
                val = 0.5
            else:
                val = 0.2
            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
                description=f"Free: {free_gb:.1f} GB",
            )
        except OSError:
            return MetricSnapshot(name=self.name, value=1.0, weight=self.weight)
