"""
CORTEX Daemon — Package init (lazy-loaded).

Re-exports from sub-modules for backward compatibility.
Uses __getattr__ to avoid eager loading of heavyweight dependencies
(e.g., watchdog via core.py → ast_oracle.py). This prevents
ModuleNotFoundError cascades when importing lightweight daemon
submodules like epistemic_breaker or models.

Ghost #4731: The previous eager init caused cortex.cli store to crash
because any `from cortex.extensions.daemon.X import Y` triggered the full import
chain including optional dependencies.
"""

from __future__ import annotations

import importlib
import socket  # noqa: F401
import ssl  # noqa: F401 — re-export for backward compat (tests patch via cortex.daemon.ssl)
import time  # noqa: F401
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.daemon.core import MoskvDaemon
    from cortex.extensions.daemon.models import (
        BUNDLE_ID,
        DEFAULT_COOLDOWN,
        DEFAULT_INTERVAL,
        DEFAULT_MEMORY_STALE_HOURS,
        DEFAULT_STALE_HOURS,
        STATUS_FILE,
        CertAlert,
        DaemonStatus,
        DiskAlert,
        EngineHealthAlert,
        EntropyAlert,
        GhostAlert,
        MejoraloAlert,
        MemoryAlert,
        PerceptionAlert,
        SiteStatus,
    )
    from cortex.extensions.daemon.monitors import (
        CertMonitor,
        DiskMonitor,
        EngineHealthCheck,
        EntropyMonitor,
        GhostWatcher,
        MemorySyncer,
        PerceptionMonitor,
        SiteMonitor,
    )
    from cortex.extensions.daemon.notifier import Notifier

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
    "MoskvDaemon": ("cortex.extensions.daemon.core", "MoskvDaemon"),
    # models
    "BUNDLE_ID": ("cortex.extensions.daemon.models", "BUNDLE_ID"),
    "DEFAULT_COOLDOWN": ("cortex.extensions.daemon.models", "DEFAULT_COOLDOWN"),
    "DEFAULT_INTERVAL": ("cortex.extensions.daemon.models", "DEFAULT_INTERVAL"),
    "DEFAULT_MEMORY_STALE_HOURS": ("cortex.extensions.daemon.models", "DEFAULT_MEMORY_STALE_HOURS"),
    "DEFAULT_STALE_HOURS": ("cortex.extensions.daemon.models", "DEFAULT_STALE_HOURS"),
    "STATUS_FILE": ("cortex.extensions.daemon.models", "STATUS_FILE"),
    "CertAlert": ("cortex.extensions.daemon.models", "CertAlert"),
    "DaemonStatus": ("cortex.extensions.daemon.models", "DaemonStatus"),
    "DiskAlert": ("cortex.extensions.daemon.models", "DiskAlert"),
    "EngineHealthAlert": ("cortex.extensions.daemon.models", "EngineHealthAlert"),
    "EntropyAlert": ("cortex.extensions.daemon.models", "EntropyAlert"),
    "GhostAlert": ("cortex.extensions.daemon.models", "GhostAlert"),
    "MejoraloAlert": ("cortex.extensions.daemon.models", "MejoraloAlert"),
    "MemoryAlert": ("cortex.extensions.daemon.models", "MemoryAlert"),
    "PerceptionAlert": ("cortex.extensions.daemon.models", "PerceptionAlert"),
    "SiteStatus": ("cortex.extensions.daemon.models", "SiteStatus"),
    # monitors
    "CertMonitor": ("cortex.extensions.daemon.monitors", "CertMonitor"),
    "DiskMonitor": ("cortex.extensions.daemon.monitors", "DiskMonitor"),
    "EngineHealthCheck": ("cortex.extensions.daemon.monitors", "EngineHealthCheck"),
    "EntropyMonitor": ("cortex.extensions.daemon.monitors", "EntropyMonitor"),
    "GhostWatcher": ("cortex.extensions.daemon.monitors", "GhostWatcher"),
    "MemorySyncer": ("cortex.extensions.daemon.monitors", "MemorySyncer"),
    "PerceptionMonitor": ("cortex.extensions.daemon.monitors", "PerceptionMonitor"),
    "SiteMonitor": ("cortex.extensions.daemon.monitors", "SiteMonitor"),
    # notifier
    "Notifier": ("cortex.extensions.daemon.notifier", "Notifier"),
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
    raise AttributeError(f"module 'cortex.extensions.daemon' has no attribute {name!r}")
