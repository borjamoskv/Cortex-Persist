# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""Metric collector entry point and registry factory.

The monolithic collector is dead. Plugin-based. O(1) lookup.
Satisfies Seal 8 (LOC Guard) via modularity.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cortex.extensions.health.collectors import BUILTINS
from cortex.extensions.health.models import MetricSnapshot
from cortex.extensions.health.registry import CollectorRegistry

logger = logging.getLogger("cortex.extensions.health.collector")

__all__ = ["CollectorRegistry", "HealthCollector", "create_default_registry"]


def create_default_registry() -> CollectorRegistry:
    """Create a registry with all built-in collectors."""
    reg = CollectorRegistry()
    for cls in BUILTINS:
        reg.register(cls())
    return reg


class HealthCollector:
    """Facade for backward compatibility.

    Wraps the CollectorRegistry so existing code still works:
    ``HealthCollector(db_path).collect_all()``
    """

    def __init__(
        self,
        db_path: str | Path = "",
        registry: CollectorRegistry | None = None,
    ) -> None:
        self._db_path = str(db_path) if db_path else ""
        self._registry = registry or create_default_registry()

    def collect_all(self) -> list[MetricSnapshot]:
        """Run all registered collectors."""
        return self._registry.collect_all(self._db_path)

    @property
    def registry(self) -> CollectorRegistry:
        """Access the underlying registry."""
        return self._registry
