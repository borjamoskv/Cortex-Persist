"""Disk usage monitor for MOSKV daemon.

Sovereign 200: Uses TTL-cached measurement to prevent O(N) rglob
on every health check cycle. Cache invalidates after 60s by default.
"""

from __future__ import annotations
from typing import Optional

import logging
import time
from pathlib import Path

from cortex.extensions.daemon.models import CORTEX_DIR, DEFAULT_DISK_WARN_MB, DiskAlert

logger = logging.getLogger("moskv-daemon")

_SKIP_DIRS = frozenset(("venv", ".venv", "__pycache__", ".git", "node_modules"))


class DiskMonitor:
    """Alerts when CORTEX directory exceeds disk threshold.

    Caches the last measurement to avoid O(N) filesystem traversal
    on every daemon tick. TTL defaults to 60 seconds.
    """

    def __init__(
        self,
        watch_path: Path = CORTEX_DIR,
        threshold_mb: int = DEFAULT_DISK_WARN_MB,
        cache_ttl_seconds: float = 60.0,
    ):
        self.watch_path = watch_path
        self.threshold_mb = threshold_mb
        self._cache_ttl = cache_ttl_seconds
        self._cached_size_mb: Optional[float] = None
        self._cache_ts: float = 0.0

    def check(self) -> list[DiskAlert]:
        """Return alert if watch_path exceeds threshold."""
        if not self.watch_path.exists():
            return []

        now = time.monotonic()
        if self._cached_size_mb is not None and (now - self._cache_ts) < self._cache_ttl:
            size_mb = self._cached_size_mb
        else:
            size_mb = self._measure_directory_size()
            self._cached_size_mb = size_mb
            self._cache_ts = now

        if size_mb > self.threshold_mb:
            return [
                DiskAlert(
                    path=str(self.watch_path),
                    size_mb=size_mb,
                    threshold_mb=self.threshold_mb,
                )
            ]
        return []

    def _measure_directory_size(self) -> float:
        """Walk directory tree and sum file sizes. O(N) but cached."""
        total = 0
        for f in self.watch_path.rglob("*"):
            if _SKIP_DIRS.intersection(f.parts):
                continue
            if not f.is_file():
                continue
            try:
                total += f.stat().st_size
            except OSError as e:
                logger.warning("Disk check error: %s", e)

        return total / 1_048_576
