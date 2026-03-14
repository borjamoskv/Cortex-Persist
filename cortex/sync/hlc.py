"""
Hybrid Logical Clock — Causal Ordering for Edge Swarms (Ω₃ / Ω₁₂).

Implements the Hybrid Logical Clock (HLC) from Kulkarni et al. (2014).
Provides causal ordering guarantees without dependence on synchronized
physical clocks — critical for edge devices with intermittent connectivity.

Properties:
  - Monotonic: every tick() > all previous timestamps
  - Causal: if event A → event B, then HLC(A) < HLC(B)
  - Bounded skew: logical counter bounded at 65535
  - Lightweight: 16 bytes total (8 physical + 4 logical + 4 node_id)

Edge-compatible: No external dependencies. Pure Python.
GPU-native: N/A (clock is CPU-bound, ~50ns per tick).

Reference: "Logical Physical Clocks and Consistent Snapshots
           in Globally Distributed Databases" (2014)
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass

__all__ = ["HybridLogicalClock", "HLCTimestamp"]

# Maximum logical counter before forcing physical clock advance
_MAX_LOGICAL = 0xFFFF  # 65535


@dataclass(frozen=True, order=True, slots=True)
class HLCTimestamp:
    """Compact causal timestamp for CRDT operations.

    Ordering: physical_ms > logical > node_id (lexicographic).
    Total size: 16 bytes when packed.
    """

    physical_ms: int
    logical: int
    node_id: int = 0

    def __repr__(self) -> str:
        return (
            f"HLC({self.physical_ms}:{self.logical:04x}"
            f"@node{self.node_id})"
        )

    def to_bytes(self) -> bytes:
        """Pack into 16 bytes: 8 (physical) + 4 (logical) + 4 (node)."""
        return struct.pack(
            "<QII", self.physical_ms, self.logical, self.node_id
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> HLCTimestamp:
        """Unpack from 16-byte binary."""
        physical_ms, logical, node_id = struct.unpack("<QII", data)
        return cls(
            physical_ms=physical_ms, logical=logical, node_id=node_id
        )

    def to_str(self) -> str:
        """Human-readable serialization for SQLite TEXT storage."""
        return f"{self.physical_ms}:{self.logical:04x}:{self.node_id}"

    @classmethod
    def from_str(cls, s: str) -> HLCTimestamp:
        """Parse from string representation."""
        parts = s.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid HLC string: {s}")
        return cls(
            physical_ms=int(parts[0]),
            logical=int(parts[1], 16),
            node_id=int(parts[2]),
        )

    @classmethod
    def zero(cls) -> HLCTimestamp:
        """The epoch — smallest possible timestamp."""
        return cls(physical_ms=0, logical=0, node_id=0)


class HybridLogicalClock:
    """Causal clock for distributed agent swarms.

    Each agent node maintains its own HLC instance.
    When agents sync, they exchange timestamps via receive()
    to establish causal ordering.

    Usage:
        clock = HybridLogicalClock(node_id=1)
        ts1 = clock.tick()          # Local event
        ts2 = clock.tick()          # Another local event (ts2 > ts1)
        ts3 = clock.receive(remote_ts)  # Merge with remote
    """

    def __init__(self, node_id: int = 0):
        self._node_id = node_id
        self._physical_ms = 0
        self._logical = 0

    @property
    def node_id(self) -> int:
        return self._node_id

    @property
    def now(self) -> HLCTimestamp:
        """Current clock state without advancing."""
        return HLCTimestamp(
            physical_ms=self._physical_ms,
            logical=self._logical,
            node_id=self._node_id,
        )

    def _wall_ms(self) -> int:
        """Physical wall clock in milliseconds."""
        return int(time.time() * 1000)

    def tick(self) -> HLCTimestamp:
        """Advance the clock for a local event.

        Guarantees monotonicity even if physical clock goes backward.
        """
        wall = self._wall_ms()

        if wall > self._physical_ms:
            self._physical_ms = wall
            self._logical = 0
        else:
            self._logical += 1
            if self._logical > _MAX_LOGICAL:
                # Force physical advance to prevent logical overflow
                self._physical_ms += 1
                self._logical = 0

        return HLCTimestamp(
            physical_ms=self._physical_ms,
            logical=self._logical,
            node_id=self._node_id,
        )

    def receive(self, remote: HLCTimestamp) -> HLCTimestamp:
        """Merge with a remote timestamp (causal receive).

        Ensures the resulting timestamp is greater than both
        the local clock and the remote timestamp.
        """
        wall = self._wall_ms()

        if wall > self._physical_ms and wall > remote.physical_ms:
            self._physical_ms = wall
            self._logical = 0
        elif self._physical_ms == remote.physical_ms:
            self._logical = max(self._logical, remote.logical) + 1
        elif self._physical_ms > remote.physical_ms:
            self._logical += 1
        else:
            self._physical_ms = remote.physical_ms
            self._logical = remote.logical + 1

        if self._logical > _MAX_LOGICAL:
            self._physical_ms += 1
            self._logical = 0

        return HLCTimestamp(
            physical_ms=self._physical_ms,
            logical=self._logical,
            node_id=self._node_id,
        )

    def reset(self) -> None:
        """Reset clock to zero. Use only in testing."""
        self._physical_ms = 0
        self._logical = 0
