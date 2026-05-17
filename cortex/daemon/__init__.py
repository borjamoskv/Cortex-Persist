"""CORTEX v0.3.0b8 — Guard Daemon.

Invisible background governance for AI agent actions.
Watches filesystem mutations, classifies actions, routes through
the guard pipeline, emits verdicts, and persists audit trail.
"""

from __future__ import annotations

__all__ = [
    "ActionClassifier",
    "GuardDaemon",
    "VerdictEmitter",
]


def __getattr__(name: str):
    import importlib

    _LAZY = {
        "ActionClassifier": ("cortex.daemon.action_classifier", "ActionClassifier"),
        "GuardDaemon": ("cortex.daemon.guard_daemon", "GuardDaemon"),
        "VerdictEmitter": ("cortex.daemon.verdict_emitter", "VerdictEmitter"),
    }
    if name in _LAZY:
        mod_path, attr = _LAZY[name]
        mod = importlib.import_module(mod_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.daemon' has no attribute {name!r}")
