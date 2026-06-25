# [C5-REAL] Exergy-Maximized
"""CORTEX Config - Backward-compatible shim.

Real implementation lives in cortex.core.config.
This module re-exports everything so existing `from legacy_research.config import X` works.
"""

from typing import Any

import legacy_research.core.config as _core
from legacy_research.core.config import reload as _core_reload


def reload() -> None:
    """Reload configuration via core module."""
    _core_reload()


def __getattr__(name: str) -> Any:
    """Lazy O(1) proxy for configuration attributes."""
    return getattr(_core, name)


def __dir__() -> list[str]:
    """Expose original core attributes to dir() and autocompletion."""
    return dir(_core)
