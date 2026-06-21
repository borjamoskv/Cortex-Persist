# [C5-REAL] Exergy-Maximized
"""Gateway.

Sovereign Signal Bus and Cross-Axiom Orchestration.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.signals.bus import SignalBus
    from cortex.gateway.router import GatewayIntent, GatewayRequest, GatewayResponse, GatewayRouter

__all__ = [
    "GatewayIntent",
    "GatewayRequest",
    "GatewayResponse",
    "GatewayRouter",
    "SignalBus",
    "I10ConsensusGateway",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "SignalBus": ("cortex.extensions.signals.bus", "SignalBus"),
    "GatewayIntent": ("cortex.gateway.router", "GatewayIntent"),
    "GatewayRequest": ("cortex.gateway.router", "GatewayRequest"),
    "GatewayResponse": ("cortex.gateway.router", "GatewayResponse"),
    "GatewayRouter": ("cortex.gateway.router", "GatewayRouter"),
    "I10ConsensusGateway": ("cortex.gateway.i10_consensus", "I10ConsensusGateway"),
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
