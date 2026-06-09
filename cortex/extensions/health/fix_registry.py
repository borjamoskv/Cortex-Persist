# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class HealthFix:
    metric: str
    description: str
    action: Callable
    params: dict[str, Any] | None = None


class FixRegistry:
    def __init__(self):
        self._fixes: dict[str, list[HealthFix]] = {}

    def register(self, metric: str, description: str, action: Callable, **params):
        if metric not in self._fixes:
            self._fixes[metric] = []
        self._fixes[metric].append(
            HealthFix(metric=metric, description=description, action=action, params=params)
        )

    def applicable_fixes(self, metrics: list[str]) -> list[HealthFix]:
        results = []
        for m in metrics:
            if m in self._fixes:
                results.extend(self._fixes[m])
        return results

    def list_fixable(self) -> list[str]:
        return sorted(list(self._fixes.keys()))
