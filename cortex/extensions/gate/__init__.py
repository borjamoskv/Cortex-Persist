from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.gate.core import SovereignGate, get_gate, reset_gate
    from cortex.extensions.gate.enums import ActionLevel, ActionStatus, GatePolicy
    from cortex.extensions.gate.errors import (
        GateError,
        GateExpired,
        GateInvalidSignature,
        GateNotApproved,
    )
    from cortex.extensions.gate.models import PendingAction

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
    "ActionLevel": ("cortex.extensions.gate.enums", "ActionLevel"),
    "ActionStatus": ("cortex.extensions.gate.enums", "ActionStatus"),
    "GateError": ("cortex.extensions.gate.errors", "GateError"),
    "GateExpired": ("cortex.extensions.gate.errors", "GateExpired"),
    "GateInvalidSignature": ("cortex.extensions.gate.errors", "GateInvalidSignature"),
    "GateNotApproved": ("cortex.extensions.gate.errors", "GateNotApproved"),
    "GatePolicy": ("cortex.extensions.gate.enums", "GatePolicy"),
    "PendingAction": ("cortex.extensions.gate.models", "PendingAction"),
    "SovereignGate": ("cortex.extensions.gate.core", "SovereignGate"),
    "get_gate": ("cortex.extensions.gate.core", "get_gate"),
    "reset_gate": ("cortex.extensions.gate.core", "reset_gate"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.extensions.gate' has no attribute {name!r}")
