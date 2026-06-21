# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.metering.quotas import PLAN_QUOTAS, QuotaEnforcer
    from cortex.extensions.metering.tracker import UsageTracker

__all__ = ["PLAN_QUOTAS", "QuotaEnforcer", "UsageTracker"]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "PLAN_QUOTAS": ("cortex.extensions.metering.quotas", "PLAN_QUOTAS"),
    "QuotaEnforcer": ("cortex.extensions.metering.quotas", "QuotaEnforcer"),
    "UsageTracker": ("cortex.extensions.metering.tracker", "UsageTracker"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.extensions.metering' has no attribute {name!r}")
