"""CORTEX v6.0 — Signal Bus (L1 Consciousness Layer).

Persistent, queryable, SQLite-backed signaling system that transforms
isolated tools into a reactive nervous system. Any tool can emit()
signals and any other can poll() for unconsumed signals — surviving
process boundaries.

Usage:
    from cortex.signals import SignalBus

    bus = SignalBus(conn)
    bus.emit("plan:done", {"project": "cortex", "files": [...]}, source="arkitetv-1")
    signals = bus.poll(event_type="plan:done", consumer="legion-1")
"""

from cortex.signals.bus import SignalBus
from cortex.signals.models import Signal, SignalFilter

__all__ = ["Signal", "SignalBus", "SignalFilter"]
