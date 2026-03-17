"""CORTEX Daemon monitors — lazy-loaded (PEP 562)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.daemon.monitors.auto_immune import AutoImmuneMonitor
    from cortex.extensions.daemon.monitors.cert import CertMonitor
    from cortex.extensions.daemon.monitors.cloud import CloudSyncMonitor
    from cortex.extensions.daemon.monitors.compaction import CompactionMonitor
    from cortex.extensions.daemon.monitors.disk import DiskMonitor
    from cortex.extensions.daemon.monitors.engine import EngineHealthCheck
    from cortex.extensions.daemon.monitors.epistemic import EpistemicMonitor
    from cortex.extensions.daemon.monitors.evaluation import EvaluationMonitor
    from cortex.extensions.daemon.monitors.ghosts import GhostWatcher
    from cortex.extensions.daemon.monitors.mejoralo import UnifiedMejoraloMonitor
    from cortex.extensions.daemon.monitors.memory import MemorySyncer
    from cortex.extensions.daemon.monitors.network import SiteMonitor
    from cortex.extensions.daemon.monitors.neural import NeuralIntentMonitor
    from cortex.extensions.daemon.monitors.perception import PerceptionMonitor
    from cortex.extensions.daemon.monitors.security import SecurityMonitor
    from cortex.extensions.daemon.monitors.signals import SignalMonitor
    from cortex.extensions.daemon.monitors.tombstone import TombstoneMonitor
    from cortex.extensions.daemon.monitors.trends import TrendsMonitor
    from cortex.extensions.daemon.monitors.workflow import WorkflowMonitor

# Aliases for backward compatibility
_ALIASES: dict[str, str] = {
    "AutonomousMejoraloMonitor": "UnifiedMejoraloMonitor",
    "EntropyMonitor": "UnifiedMejoraloMonitor",
}

__all__ = [
    "AutoImmuneMonitor",
    "AutonomousMejoraloMonitor",
    "CertMonitor",
    "CloudSyncMonitor",
    "CompactionMonitor",
    "DiskMonitor",
    "EngineHealthCheck",
    "EntropyMonitor",
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
    "EpistemicMonitor",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AutoImmuneMonitor": ("cortex.extensions.daemon.monitors.auto_immune", "AutoImmuneMonitor"),
    "CertMonitor": ("cortex.extensions.daemon.monitors.cert", "CertMonitor"),
    "CloudSyncMonitor": ("cortex.extensions.daemon.monitors.cloud", "CloudSyncMonitor"),
    "CompactionMonitor": ("cortex.extensions.daemon.monitors.compaction", "CompactionMonitor"),
    "DiskMonitor": ("cortex.extensions.daemon.monitors.disk", "DiskMonitor"),
    "EngineHealthCheck": ("cortex.extensions.daemon.monitors.engine", "EngineHealthCheck"),
    "EvaluationMonitor": ("cortex.extensions.daemon.monitors.evaluation", "EvaluationMonitor"),
    "GhostWatcher": ("cortex.extensions.daemon.monitors.ghosts", "GhostWatcher"),
    "MemorySyncer": ("cortex.extensions.daemon.monitors.memory", "MemorySyncer"),
    "NeuralIntentMonitor": ("cortex.extensions.daemon.monitors.neural", "NeuralIntentMonitor"),
    "PerceptionMonitor": ("cortex.extensions.daemon.monitors.perception", "PerceptionMonitor"),
    "SecurityMonitor": ("cortex.extensions.daemon.monitors.security", "SecurityMonitor"),
    "SignalMonitor": ("cortex.extensions.daemon.monitors.signals", "SignalMonitor"),
    "SiteMonitor": ("cortex.extensions.daemon.monitors.network", "SiteMonitor"),
    "TombstoneMonitor": ("cortex.extensions.daemon.monitors.tombstone", "TombstoneMonitor"),
    "TrendsMonitor": ("cortex.extensions.daemon.monitors.trends", "TrendsMonitor"),
    "UnifiedMejoraloMonitor": ("cortex.extensions.daemon.monitors.mejoralo", "UnifiedMejoraloMonitor"),
    "WorkflowMonitor": ("cortex.extensions.daemon.monitors.workflow", "WorkflowMonitor"),
    "EpistemicMonitor": ("cortex.extensions.daemon.monitors.epistemic", "EpistemicMonitor"),
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
    raise AttributeError(f"module 'cortex.extensions.daemon.monitors' has no attribute {name!r}")
