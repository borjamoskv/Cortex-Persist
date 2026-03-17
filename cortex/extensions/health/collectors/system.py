# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""OS and system health collectors."""

from __future__ import annotations

import os
import subprocess

from cortex.extensions.health.models import MetricSnapshot


class SystemLoadCollector:
    """OS-level system load (1m/5m/15m) measurement."""

    @property
    def name(self) -> str:
        return "sysload"

    @property
    def weight(self) -> float:
        return 1.0

    @property
    def description(self) -> str:
        return "1-minute system load average vs CPU core count."

    @property
    def remediation(self) -> str:
        return "High load detected. Throttle agent concurrency or pause NightShift."

    def collect(self, db_path: str) -> MetricSnapshot:
        try:
            load_1m, _, _ = os.getloadavg()
            cores = os.cpu_count() or 4

            # Load > Cores means processes are waiting for CPU
            ratio = load_1m / cores

            if ratio < 0.7:
                val = 1.0
            elif ratio < 1.0:
                val = 0.8
            elif ratio < 1.5:
                val = 0.5
            else:
                val = 0.2

            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
                description=f"Load: {load_1m:.2f} (Cores: {cores})",
            )
        except (OSError, AttributeError):
            return MetricSnapshot(
                name=self.name,
                value=1.0,  # Assume healthy if unsupported
                weight=self.weight,
            )


class OrphanedBrowserCollector:
    """Identify orphaned ms-playwright-go processes."""

    @property
    def name(self) -> str:
        return "browsers"

    @property
    def weight(self) -> float:
        return 0.5

    @property
    def description(self) -> str:
        return "Orphaned browser process count."

    @property
    def remediation(self) -> str:
        return "Kill orphaned browsers via `pkill -f ms-playwright-go`."

    def collect(self, db_path: str) -> MetricSnapshot:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "ms-playwright-go"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
            val = 1.0 if count == 0 else max(0.2, 1.0 - count * 0.2)
            return MetricSnapshot(
                name=self.name,
                value=val,
                weight=self.weight,
                description=f"Orphaned processes: {count}",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return MetricSnapshot(name=self.name, value=1.0, weight=self.weight)
