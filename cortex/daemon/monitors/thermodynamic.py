"""Thermodynamic Memory monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.daemon.models import ThermodynamicAlert
from cortex.memory.homeostasis import EntropyPruner

logger = logging.getLogger("moskv-daemon")


class ThermodynamicMemoryMonitor:
    """Circadian memory syncer simulating ATP-constrained biological pruning."""

    def __init__(
        self,
        manager: Any,
        tenants: list[str],
        interval_seconds: int = 14400,  # 4 hours
        atp_threshold: float = 0.2,
    ):
        self.manager = manager
        self.tenants = tenants
        self.interval_seconds = interval_seconds
        self.atp_threshold = atp_threshold
        self._last_runs: dict[str, float] = {}

    def check(self) -> list[ThermodynamicAlert]:
        """Execute thermodynamic pruning cycle over enrolled tenants."""
        if not self.manager or getattr(self.manager, "_l2", None) is None:
            return []

        alerts: list[ThermodynamicAlert] = []
        now = time.monotonic()

        pruner = EntropyPruner(self.manager._l2, atp_threshold=self.atp_threshold)

        for tenant in self.tenants:
            last_run = self._last_runs.get(tenant, 0)
            if now - last_run < self.interval_seconds:
                continue

            try:
                import asyncio

                # For safety, we run it within the current thread loop or default loop
                try:
                    loop = asyncio.get_running_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        pruner.prune_cycle(tenant_id=tenant), loop
                    )
                    pruned_count = future.result(timeout=60.0)
                except RuntimeError:
                    pruned_count = asyncio.run(pruner.prune_cycle(tenant_id=tenant))

                self._last_runs[tenant] = now

                if pruned_count > 0:
                    alerts.append(
                        ThermodynamicAlert(
                            tenant_id=tenant,
                            pruned_count=pruned_count,
                            message=f"Termodinámica en L2: {pruned_count} engramas entrópicos purgados.",
                        )
                    )
                    logger.info(
                        "✅ Poda Sináptica completada (tenant=%s): -%d engramas",
                        tenant,
                        pruned_count,
                    )

            except Exception as e:
                logger.error("Thermodynamic Memory monitor failed on %s: %s", tenant, e)

        return alerts
