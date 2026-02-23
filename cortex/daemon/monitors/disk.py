"""Disk usage monitor for MOSKV daemon."""

from __future__ import annotations

import logging
from pathlib import Path

from cortex.daemon.models import CORTEX_DIR, DEFAULT_DISK_WARN_MB, DiskAlert

logger = logging.getLogger("moskv-daemon")


class DiskMonitor:
    """Alerts when CORTEX directory exceeds disk threshold."""

    def __init__(
        self,
        watch_path: Path = CORTEX_DIR,
        threshold_mb: int = DEFAULT_DISK_WARN_MB,
    ):
        self.watch_path = watch_path
        self.threshold_mb = threshold_mb

    def check(self) -> list[DiskAlert]:
        """Return alert if watch_path exceeds threshold."""
        if not self.watch_path.exists():
            return []

        total = 0
        for f in self.watch_path.rglob("*"):
            if not f.is_file():
                continue
            try:
                total += f.stat().st_size
            except OSError as e:
                logger.warning("Disk check error: %s", e)

        size_mb = total / 1_048_576
        if size_mb > self.threshold_mb:
            return [
                DiskAlert(
                    path=str(self.watch_path),
                    size_mb=size_mb,
                    threshold_mb=self.threshold_mb,
                )
            ]
        return []
