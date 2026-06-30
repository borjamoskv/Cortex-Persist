# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from babylon60.extensions.daemon.monitors.auto_immune import AutoImmuneMonitor
    from babylon60.extensions.daemon.monitors.cert import CertMonitor
    from babylon60.extensions.daemon.monitors.cloud import CloudSyncMonitor
    from babylon60.extensions.daemon.monitors.compaction import CompactionMonitor
    from babylon60.extensions.daemon.monitors.disk import DiskMonitor
    from babylon60.extensions.daemon.monitors.engine import EngineHealthCheck
    from babylon60.extensions.daemon.monitors.epistemic import EpistemicMonitor
    from babylon60.extensions.daemon.monitors.evaluation import EvaluationMonitor
    from babylon60.extensions.daemon.monitors.ghosts import GhostWatcher
    from babylon60.extensions.daemon.monitors.mejoralo import UnifiedMejoraloMonitor
    from babylon60.extensions.daemon.monitors.memory import MemorySyncer
    from babylon60.extensions.daemon.monitors.network import SiteMonitor
    from babylon60.extensions.daemon.monitors.neural import NeuralIntentMonitor
    from babylon60.extensions.daemon.monitors.perception import PerceptionMonitor
    from babylon60.extensions.daemon.monitors.security import SecurityMonitor
    from babylon60.extensions.daemon.monitors.signals import SignalMonitor
    from babylon60.extensions.daemon.monitors.tombstone import TombstoneMonitor
    from babylon60.extensions.daemon.monitors.trends import TrendsMonitor
    from babylon60.extensions.daemon.monitors.workflow import WorkflowMonitor

# Aliases for backward compatibility
_ALIASES: dict[str, str] = {
    "AutonomousMejoraloMonitor": "UnifiedMejoraloMonitor",
    "EntropyMonitor": "UnifiedMejoraloMonitor",
}

__all__ = [
    "AutoImmuneMonitor",
    "AutonomousMejoraloMonitor",  # pyright: ignore[reportUnsupportedDunderAll]
    "CertMonitor",
    "CloudSyncMonitor",
    "CompactionMonitor",
    "DiskMonitor",
    "EngineHealthCheck",
    "EntropyMonitor",  # pyright: ignore[reportUnsupportedDunderAll]
    "EpistemicMonitor",
    "EvaluationMonitor",
    "GhostWatcher",
    "MemorySyncer",
    "NeuralIntentMonitor",
    "PerceptionMonitor",
    "SecurityMonitor",
    "SignalMonitor",
    "SiteMonitor",
    "TombstoneMonitor",
    "TrendsMonitor",
    "UnifiedMejoraloMonitor",
    "WorkflowMonitor",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AutoImmuneMonitor": ("cortex_extensions.daemon.monitors.auto_immune", "AutoImmuneMonitor"),
    "CertMonitor": ("cortex_extensions.daemon.monitors.cert", "CertMonitor"),
    "CloudSyncMonitor": ("cortex_extensions.daemon.monitors.cloud", "CloudSyncMonitor"),
    "CompactionMonitor": ("cortex_extensions.daemon.monitors.compaction", "CompactionMonitor"),
    "DiskMonitor": ("cortex_extensions.daemon.monitors.disk", "DiskMonitor"),
    "EngineHealthCheck": ("cortex_extensions.daemon.monitors.engine", "EngineHealthCheck"),
    "EvaluationMonitor": ("cortex_extensions.daemon.monitors.evaluation", "EvaluationMonitor"),
    "GhostWatcher": ("cortex_extensions.daemon.monitors.ghosts", "GhostWatcher"),
    "MemorySyncer": ("cortex_extensions.daemon.monitors.memory", "MemorySyncer"),
    "NeuralIntentMonitor": ("cortex_extensions.daemon.monitors.neural", "NeuralIntentMonitor"),
    "PerceptionMonitor": ("cortex_extensions.daemon.monitors.perception", "PerceptionMonitor"),
    "SecurityMonitor": ("cortex_extensions.daemon.monitors.security", "SecurityMonitor"),
    "SignalMonitor": ("cortex_extensions.daemon.monitors.signals", "SignalMonitor"),
    "SiteMonitor": ("cortex_extensions.daemon.monitors.network", "SiteMonitor"),
    "TombstoneMonitor": ("cortex_extensions.daemon.monitors.tombstone", "TombstoneMonitor"),
    "TrendsMonitor": ("cortex_extensions.daemon.monitors.trends", "TrendsMonitor"),
    "UnifiedMejoraloMonitor": (
        "cortex_extensions.daemon.monitors.mejoralo",
        "UnifiedMejoraloMonitor",
    ),
    "WorkflowMonitor": ("cortex_extensions.daemon.monitors.workflow", "WorkflowMonitor"),
    "EpistemicMonitor": ("cortex_extensions.daemon.monitors.epistemic", "EpistemicMonitor"),
}


def __getattr__(name: str) -> object:
    """Lazy-load monitor symbols on first access (PEP 562)."""
    # Handle aliases first
    if name in _ALIASES:
        canonical = _ALIASES[name]
        value = __getattr__(canonical)
        globals()[name] = value
        return value

    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex_extensions.daemon.monitors' has no attribute {name!r}")
