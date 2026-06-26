# [C5-REAL] Exergy-Maximized
"""Gateway.

Sovereign Signal Bus and Cross-Axiom Orchestration.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.gateway.router import GatewayIntent, GatewayRequest, GatewayResponse, GatewayRouter
    from cortex_extensions.signals.bus import SignalBus

__all__ = [
    "GatewayIntent",
    "GatewayRequest",
    "GatewayResponse",
    "GatewayRouter",
    "SignalBus",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "SignalBus": ("cortex_extensions.signals.bus", "SignalBus"),
    "GatewayIntent": ("cortex.gateway.router", "GatewayIntent"),
    "GatewayRequest": ("cortex.gateway.router", "GatewayRequest"),
    "GatewayResponse": ("cortex.gateway.router", "GatewayResponse"),
    "GatewayRouter": ("cortex.gateway.router", "GatewayRouter"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.gateway' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
