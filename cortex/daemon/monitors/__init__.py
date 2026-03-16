"""CORTEX Daemon monitors — lazy-loaded (PEP 562)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.daemon.monitors.auto_immune import AutoImmuneMonitor
    from cortex.daemon.monitors.cert import CertMonitor
    from cortex.daemon.monitors.cloud import CloudSyncMonitor
    from cortex.daemon.monitors.compaction import CompactionMonitor
    from cortex.daemon.monitors.disk import DiskMonitor
    from cortex.daemon.monitors.engine import EngineHealthCheck
    from cortex.daemon.monitors.epistemic import EpistemicMonitor
    from cortex.daemon.monitors.evaluation import EvaluationMonitor
    from cortex.daemon.monitors.ghosts import GhostWatcher
    from cortex.daemon.monitors.mejoralo import UnifiedMejoraloMonitor
    from cortex.daemon.monitors.memory import MemorySyncer
    from cortex.daemon.monitors.network import SiteMonitor
    from cortex.daemon.monitors.neural import NeuralIntentMonitor
    from cortex.daemon.monitors.perception import PerceptionMonitor
    from cortex.daemon.monitors.security import SecurityMonitor
    from cortex.daemon.monitors.signals import SignalMonitor
    from cortex.daemon.monitors.tombstone import TombstoneMonitor
    from cortex.daemon.monitors.trends import TrendsMonitor
    from cortex.daemon.monitors.workflow import WorkflowMonitor

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
    "AutoImmuneMonitor": ("cortex.daemon.monitors.auto_immune", "AutoImmuneMonitor"),
    "CertMonitor": ("cortex.daemon.monitors.cert", "CertMonitor"),
    "CloudSyncMonitor": ("cortex.daemon.monitors.cloud", "CloudSyncMonitor"),
    "CompactionMonitor": ("cortex.daemon.monitors.compaction", "CompactionMonitor"),
    "DiskMonitor": ("cortex.daemon.monitors.disk", "DiskMonitor"),
    "EngineHealthCheck": ("cortex.daemon.monitors.engine", "EngineHealthCheck"),
    "EvaluationMonitor": ("cortex.daemon.monitors.evaluation", "EvaluationMonitor"),
    "GhostWatcher": ("cortex.daemon.monitors.ghosts", "GhostWatcher"),
    "MemorySyncer": ("cortex.daemon.monitors.memory", "MemorySyncer"),
    "NeuralIntentMonitor": ("cortex.daemon.monitors.neural", "NeuralIntentMonitor"),
    "PerceptionMonitor": ("cortex.daemon.monitors.perception", "PerceptionMonitor"),
    "SecurityMonitor": ("cortex.daemon.monitors.security", "SecurityMonitor"),
    "SignalMonitor": ("cortex.daemon.monitors.signals", "SignalMonitor"),
    "SiteMonitor": ("cortex.daemon.monitors.network", "SiteMonitor"),
    "TombstoneMonitor": ("cortex.daemon.monitors.tombstone", "TombstoneMonitor"),
    "TrendsMonitor": ("cortex.daemon.monitors.trends", "TrendsMonitor"),
    "UnifiedMejoraloMonitor": ("cortex.daemon.monitors.mejoralo", "UnifiedMejoraloMonitor"),
    "WorkflowMonitor": ("cortex.daemon.monitors.workflow", "WorkflowMonitor"),
    "EpistemicMonitor": ("cortex.daemon.monitors.epistemic", "EpistemicMonitor"),
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
    raise AttributeError(f"module 'cortex.daemon.monitors' has no attribute {name!r}")
