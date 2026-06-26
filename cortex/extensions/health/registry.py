# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.extensions.health.models import MetricSnapshot

logger = logging.getLogger("cortex_extensions.health.registry")


class CollectorRegistry:
    """Plugin registry for metric collectors.

    Enforces MetricCollectorProtocol at registration time.
    Duplicate names are rejected.
    """

    def __init__(self) -> None:
        self._collectors: dict[str, MetricCollectorProtocol] = {}

    def register(self, collector: Any) -> None:
        """Register a collector. Rejects non-conforming objects."""
        if not isinstance(collector, MetricCollectorProtocol):
            raise TypeError(
                f"{type(collector).__name__} does not implement MetricCollectorProtocol"
            )
        name = collector.name
        if name in self._collectors:
            raise ValueError(f"Collector '{name}' already registered")
        self._collectors[name] = collector
        logger.debug("Registered health collector: %s", name)

    def unregister(self, name: str) -> None:
        """Remove a collector by name."""
        self._collectors.pop(name, None)

    def list_collectors(self) -> list[str]:
        """Return registered collector names."""
        return list(self._collectors.keys())

    def collect_all(self, db_path: str) -> list[MetricSnapshot]:
        """Run all registered collectors and measure latency."""
        results: list[MetricSnapshot] = []
        for name, collector in self._collectors.items():
            t0 = time.perf_counter()
            try:
                snap = collector.collect(db_path)
                latency = (time.perf_counter() - t0) * 1000.0

                # Enrich snapshot with collector metadata and timing
                object.__setattr__(snap, "latency_ms", latency)
                if not getattr(snap, "description", None):
                    object.__setattr__(snap, "description", getattr(collector, "description", ""))
                if not getattr(snap, "remediation", None):
                    object.__setattr__(snap, "remediation", getattr(collector, "remediation", ""))

                results.append(snap)
            except Exception as e:
                latency = (time.perf_counter() - t0) * 1000.0
                logger.warning(
                    "Collector %s failed: %s",
                    name,
                    e,
                )
                results.append(
                    MetricSnapshot(
                        name=name,
                        value=0.0,
                        weight=collector.weight,
                        latency_ms=latency,
                        description=getattr(collector, "description", ""),
                        remediation=f"Error collecting metric: {e}",
                    )
                )
        return results

    def __len__(self) -> int:
        return len(self._collectors)

    def __bool__(self) -> bool:
        """A registry is always truthy, even if empty.

        Prevents the 'registry or default' bug where len==0 makes bool==False.
        """
        return True

    def __contains__(self, name: str) -> bool:
        return name in self._collectors
