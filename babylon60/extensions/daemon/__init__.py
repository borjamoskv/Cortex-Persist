# [C5-REAL] Exergy-Maximized
"""
CORTEX Daemon - Package init (lazy-loaded).

Re-exports from sub-modules for backward compatibility.
Uses __getattr__ to avoid eager loading of heavyweight dependencies
(e.g., watchdog via core.py → ast_oracle.py). This prevents
ModuleNotFoundError cascades when importing lightweight daemon
submodules like epistemic_breaker or models.

Ghost #4731: The previous eager init caused cortex.cli store to crash
because any `from babylon60.extensions.daemon.X import Y` triggered the full import
chain including optional dependencies.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.extensions.daemon.core import MoskvDaemon
    from babylon60.extensions.daemon.models import (
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
    from babylon60.extensions.daemon.monitors import (
        CertMonitor,
        DiskMonitor,
        EngineHealthCheck,
        EntropyMonitor,
        GhostWatcher,
        MemorySyncer,
        PerceptionMonitor,
        SiteMonitor,
    )
    from babylon60.extensions.daemon.notifier import Notifier

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
    "MoskvDaemon": ("cortex_extensions.daemon.core", "MoskvDaemon"),
    # models
    "BUNDLE_ID": ("cortex_extensions.daemon.models", "BUNDLE_ID"),
    "DEFAULT_COOLDOWN": ("cortex_extensions.daemon.models", "DEFAULT_COOLDOWN"),
    "DEFAULT_INTERVAL": ("cortex_extensions.daemon.models", "DEFAULT_INTERVAL"),
    "DEFAULT_MEMORY_STALE_HOURS": ("cortex_extensions.daemon.models", "DEFAULT_MEMORY_STALE_HOURS"),
    "DEFAULT_STALE_HOURS": ("cortex_extensions.daemon.models", "DEFAULT_STALE_HOURS"),
    "STATUS_FILE": ("cortex_extensions.daemon.models", "STATUS_FILE"),
    "CertAlert": ("cortex_extensions.daemon.models", "CertAlert"),
    "DaemonStatus": ("cortex_extensions.daemon.models", "DaemonStatus"),
    "DiskAlert": ("cortex_extensions.daemon.models", "DiskAlert"),
    "EngineHealthAlert": ("cortex_extensions.daemon.models", "EngineHealthAlert"),
    "EntropyAlert": ("cortex_extensions.daemon.models", "EntropyAlert"),
    "GhostAlert": ("cortex_extensions.daemon.models", "GhostAlert"),
    "MejoraloAlert": ("cortex_extensions.daemon.models", "MejoraloAlert"),
    "MemoryAlert": ("cortex_extensions.daemon.models", "MemoryAlert"),
    "PerceptionAlert": ("cortex_extensions.daemon.models", "PerceptionAlert"),
    "SiteStatus": ("cortex_extensions.daemon.models", "SiteStatus"),
    # monitors
    "CertMonitor": ("cortex_extensions.daemon.monitors", "CertMonitor"),
    "DiskMonitor": ("cortex_extensions.daemon.monitors", "DiskMonitor"),
    "EngineHealthCheck": ("cortex_extensions.daemon.monitors", "EngineHealthCheck"),
    "EntropyMonitor": ("cortex_extensions.daemon.monitors", "EntropyMonitor"),
    "GhostWatcher": ("cortex_extensions.daemon.monitors", "GhostWatcher"),
    "MemorySyncer": ("cortex_extensions.daemon.monitors", "MemorySyncer"),
    "PerceptionMonitor": ("cortex_extensions.daemon.monitors", "PerceptionMonitor"),
    "SiteMonitor": ("cortex_extensions.daemon.monitors", "SiteMonitor"),
    # notifier
    "Notifier": ("cortex_extensions.daemon.notifier", "Notifier"),
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
    raise AttributeError(f"module 'cortex_extensions.daemon' has no attribute {name!r}")
