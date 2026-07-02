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
    "DaemonOmega",
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
    "MoskvDaemon": ("babylon60.extensions.daemon.core", "MoskvDaemon"),
    "DaemonOmega": ("babylon60.extensions.daemon.daemon_omega", "DaemonOmega"),
    # models
    "BUNDLE_ID": ("babylon60.extensions.daemon.models", "BUNDLE_ID"),
    "DEFAULT_COOLDOWN": ("babylon60.extensions.daemon.models", "DEFAULT_COOLDOWN"),
    "DEFAULT_INTERVAL": ("babylon60.extensions.daemon.models", "DEFAULT_INTERVAL"),
    "DEFAULT_MEMORY_STALE_HOURS": (
        "babylon60.extensions.daemon.models",
        "DEFAULT_MEMORY_STALE_HOURS",
    ),
    "DEFAULT_STALE_HOURS": ("babylon60.extensions.daemon.models", "DEFAULT_STALE_HOURS"),
    "STATUS_FILE": ("babylon60.extensions.daemon.models", "STATUS_FILE"),
    "CertAlert": ("babylon60.extensions.daemon.models", "CertAlert"),
    "DaemonStatus": ("babylon60.extensions.daemon.models", "DaemonStatus"),
    "DiskAlert": ("babylon60.extensions.daemon.models", "DiskAlert"),
    "EngineHealthAlert": ("babylon60.extensions.daemon.models", "EngineHealthAlert"),
    "EntropyAlert": ("babylon60.extensions.daemon.models", "EntropyAlert"),
    "GhostAlert": ("babylon60.extensions.daemon.models", "GhostAlert"),
    "MejoraloAlert": ("babylon60.extensions.daemon.models", "MejoraloAlert"),
    "MemoryAlert": ("babylon60.extensions.daemon.models", "MemoryAlert"),
    "PerceptionAlert": ("babylon60.extensions.daemon.models", "PerceptionAlert"),
    "SiteStatus": ("babylon60.extensions.daemon.models", "SiteStatus"),
    # monitors
    "CertMonitor": ("babylon60.extensions.daemon.monitors", "CertMonitor"),
    "DiskMonitor": ("babylon60.extensions.daemon.monitors", "DiskMonitor"),
    "EngineHealthCheck": ("babylon60.extensions.daemon.monitors", "EngineHealthCheck"),
    "EntropyMonitor": ("babylon60.extensions.daemon.monitors", "EntropyMonitor"),
    "GhostWatcher": ("babylon60.extensions.daemon.monitors", "GhostWatcher"),
    "MemorySyncer": ("babylon60.extensions.daemon.monitors", "MemorySyncer"),
    "PerceptionMonitor": ("babylon60.extensions.daemon.monitors", "PerceptionMonitor"),
    "SiteMonitor": ("babylon60.extensions.daemon.monitors", "SiteMonitor"),
    # notifier
    "Notifier": ("babylon60.extensions.daemon.notifier", "Notifier"),
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
    raise AttributeError(f"module 'babylon60.extensions.daemon' has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy-loaded symbols to dir() function calls."""
    return sorted(list(globals().keys()) + list(_LAZY_IMPORTS.keys()))
