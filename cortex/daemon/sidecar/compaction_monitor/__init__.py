"""Compaction Monitor Sidecar package.

Exports:
- ``MemoryPressureMonitor`` — async OS-level memory pressure monitor (canonical).
- ``AsyncCompactionMonitor`` — backward-compat alias for MemoryPressureMonitor.
- ``MemoryPressureAlert`` — alert dataclass emitted on pressure events.
- ``MemorySnapshot`` — cross-platform memory stats snapshot.
"""

from cortex.daemon.sidecar.compaction_monitor.monitor import (
    AsyncCompactionMonitor,  # backward-compat alias
    MemoryPressureAlert,
    MemoryPressureMonitor,
    MemorySnapshot,
)

__all__ = [
    "AsyncCompactionMonitor",
    "MemoryPressureAlert",
    "MemoryPressureMonitor",
    "MemorySnapshot",
]
