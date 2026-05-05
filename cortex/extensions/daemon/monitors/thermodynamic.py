"""Thermodynamic Memory monitor for MOSKV daemon."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from typing import Any

from cortex.memory.homeostasis import EntropyPruner

logger = logging.getLogger("moskv-daemon")


@dataclasses.dataclass
class ThermodynamicAlert:
    """Alert describing a thermodynamic memory pruning event."""

    tenant_id: str
    pruned_count: int
    message: str


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
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.check_async())

        # Already inside an event loop.
        if not hasattr(self, "_bg_tasks"):
            self._bg_tasks: set[asyncio.Task[list[ThermodynamicAlert]]] = set()

        task = asyncio.create_task(self.check_async())
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return []

    async def check_async(self) -> list[ThermodynamicAlert]:
        """Async version of check()."""
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
                pruned_count = await pruner.prune_cycle(tenant_id=tenant)

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

            except (RuntimeError, ValueError, OSError):
                logger.exception("Thermodynamic Memory monitor failed on %s", tenant)

        return alerts
