# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex_extensions.signals.bus import SignalBus
    from cortex_extensions.signals.models import Signal, SignalFilter

__all__ = ["Signal", "SignalBus", "SignalFilter"]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Signal": ("cortex_extensions.signals.models", "Signal"),
    "SignalBus": ("cortex_extensions.signals.bus", "SignalBus"),
    "SignalFilter": ("cortex_extensions.signals.models", "SignalFilter"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex_extensions.signals' has no attribute {name!r}")
