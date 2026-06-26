# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex_extensions.gate.core import SovereignGate, get_gate, reset_gate
    from cortex_extensions.gate.enums import ActionLevel, ActionStatus, GatePolicy
    from cortex_extensions.gate.errors import (
        GateError,
        GateExpired,
        GateInvalidSignature,
        GateNotApproved,
    )
    from cortex_extensions.gate.models import PendingAction

__all__ = [
    "ActionLevel",
    "ActionStatus",
    "GateError",
    "GateExpired",
    "GateInvalidSignature",
    "GateNotApproved",
    "GatePolicy",
    "PendingAction",
    "SovereignGate",
    "get_gate",
    "reset_gate",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "ActionLevel": ("cortex_extensions.gate.enums", "ActionLevel"),
    "ActionStatus": ("cortex_extensions.gate.enums", "ActionStatus"),
    "GateError": ("cortex_extensions.gate.errors", "GateError"),
    "GateExpired": ("cortex_extensions.gate.errors", "GateExpired"),
    "GateInvalidSignature": ("cortex_extensions.gate.errors", "GateInvalidSignature"),
    "GateNotApproved": ("cortex_extensions.gate.errors", "GateNotApproved"),
    "GatePolicy": ("cortex_extensions.gate.enums", "GatePolicy"),
    "PendingAction": ("cortex_extensions.gate.models", "PendingAction"),
    "SovereignGate": ("cortex_extensions.gate.core", "SovereignGate"),
    "get_gate": ("cortex_extensions.gate.core", "get_gate"),
    "reset_gate": ("cortex_extensions.gate.core", "reset_gate"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex_extensions.gate' has no attribute {name!r}")
