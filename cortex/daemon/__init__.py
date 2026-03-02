"""
CORTEX Daemon — Package init (lazy-loaded).

Re-exports from sub-modules for backward compatibility.
Uses __getattr__ to avoid eager loading of heavyweight dependencies
(e.g., watchdog via core.py → ast_oracle.py). This prevents
ModuleNotFoundError cascades when importing lightweight daemon
submodules like epistemic_breaker or models.

Ghost #4731: The previous eager init caused cortex.cli store to crash
because any `from cortex.daemon.X import Y` triggered the full import
chain including optional dependencies.
"""

from __future__ import annotations

import importlib
import socket  # noqa: F401
import ssl  # noqa: F401 — re-export for backward compat (tests patch via cortex.daemon.ssl)
import time  # noqa: F401

__all__ = [
    # core
    "MoskvDaemon",
    # models
    "BUNDLE_ID",
    "DEFAULT_COOLDOWN",
    "DEFAULT_INTERVAL",
    "DEFAULT_MEMORY_STALE_HOURS",
    "DEFAULT_STALE_HOURS",
    "STATUS_FILE",
    "CertAlert",
    "DaemonStatus",
    "DiskAlert",
    "EngineHealthAlert",
    "EntropyAlert",
    "GhostAlert",
    "MejoraloAlert",
    "MemoryAlert",
    "PerceptionAlert",
    "SiteStatus",
    # monitors
    "CertMonitor",
    "DiskMonitor",
    "EngineHealthCheck",
    "EntropyMonitor",
    "GhostWatcher",
    "MemorySyncer",
    "PerceptionMonitor",
    "SiteMonitor",
    # notifier
    "Notifier",
]

# Lazy-load map: attribute name → (module_path, attr_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # core
    "MoskvDaemon": ("cortex.daemon.core", "MoskvDaemon"),
    # models
    "BUNDLE_ID": ("cortex.daemon.models", "BUNDLE_ID"),
    "DEFAULT_COOLDOWN": ("cortex.daemon.models", "DEFAULT_COOLDOWN"),
    "DEFAULT_INTERVAL": ("cortex.daemon.models", "DEFAULT_INTERVAL"),
    "DEFAULT_MEMORY_STALE_HOURS": ("cortex.daemon.models", "DEFAULT_MEMORY_STALE_HOURS"),
    "DEFAULT_STALE_HOURS": ("cortex.daemon.models", "DEFAULT_STALE_HOURS"),
    "STATUS_FILE": ("cortex.daemon.models", "STATUS_FILE"),
    "CertAlert": ("cortex.daemon.models", "CertAlert"),
    "DaemonStatus": ("cortex.daemon.models", "DaemonStatus"),
    "DiskAlert": ("cortex.daemon.models", "DiskAlert"),
    "EngineHealthAlert": ("cortex.daemon.models", "EngineHealthAlert"),
    "EntropyAlert": ("cortex.daemon.models", "EntropyAlert"),
    "GhostAlert": ("cortex.daemon.models", "GhostAlert"),
    "MejoraloAlert": ("cortex.daemon.models", "MejoraloAlert"),
    "MemoryAlert": ("cortex.daemon.models", "MemoryAlert"),
    "PerceptionAlert": ("cortex.daemon.models", "PerceptionAlert"),
    "SiteStatus": ("cortex.daemon.models", "SiteStatus"),
    # monitors
    "CertMonitor": ("cortex.daemon.monitors", "CertMonitor"),
    "DiskMonitor": ("cortex.daemon.monitors", "DiskMonitor"),
    "EngineHealthCheck": ("cortex.daemon.monitors", "EngineHealthCheck"),
    "EntropyMonitor": ("cortex.daemon.monitors", "EntropyMonitor"),
    "GhostWatcher": ("cortex.daemon.monitors", "GhostWatcher"),
    "MemorySyncer": ("cortex.daemon.monitors", "MemorySyncer"),
    "PerceptionMonitor": ("cortex.daemon.monitors", "PerceptionMonitor"),
    "SiteMonitor": ("cortex.daemon.monitors", "SiteMonitor"),
    # notifier
    "Notifier": ("cortex.daemon.notifier", "Notifier"),
}


def __getattr__(name: str) -> object:
    """Lazy-load daemon symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        # Cache on module dict for O(1) subsequent access
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.daemon' has no attribute {name!r}")
