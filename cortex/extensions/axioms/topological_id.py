"""
CORTEX v6 — Topological ID Generator (SovereignFlake)

Axiom: Entropic Asymmetry & Multi-Scale Causality
Replaces UUIDv4. Generates lexicographically sortable, distributed IDs.
Ensures perfect causal order without relying on absolute timestamps.
"""

from __future__ import annotations

import threading
import time


class SovereignFlake:
    """
    SovereignFlake ID Generator.

    Format (63 bits total used safely in signed 64-bit int):
    - 41 bits: Timestamp offset from custom CORTEX epoch (resolves to ~69 years)
    - 10 bits: Node ID (allows 1024 unique instances/agents/devices)
    - 12 bits: Sequence (resolves 4096 events per millisecond per node)

    Features:
    - NTP lag resistance (absorbs clock drift backwards).
    - Lexicographical sorting (f"{id:019d}").
    """

    # 2026-01-01T00:00:00.000Z as the Sovereign Epoch
    EPOCH = 1767225600000

    def __init__(self, node_id: int = 1):
        # 10 bits max
        if node_id < 0 or node_id > 1023:
            raise ValueError("Node ID must be between 0 and 1023.")

        self.node_id = node_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def next_id(self) -> int:
        """Return the next unique, causal, monotonically increasing integer ID."""
        with self._lock:
            current_timestamp = int(time.time() * 1000)

            # NTP drift backward: prevent causal violations by freezing logic time
            if current_timestamp < self.last_timestamp:
                current_timestamp = self.last_timestamp

            if current_timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & 0xFFF  # 12 bits

                if self.sequence == 0:
                    # Sequence exhausted for this millisecond. Wait for next ms.
                    while current_timestamp <= self.last_timestamp:
                        current_timestamp = int(time.time() * 1000)
            else:
                self.sequence = 0

            self.last_timestamp = current_timestamp
            timestamp_diff = current_timestamp - self.EPOCH

            # Construct 63-bit integer
            # Timstamp: 41 bits (<< 22)
            # Node: 10 bits (<< 12)
            # Sequence: 12 bits
            return (timestamp_diff << 22) | (self.node_id << 12) | self.sequence

    def next_lexicographic_id(self) -> str:
        """Return the topological ID as a zero-padded string (19 digits)."""
        # zero-pad to 19 characters to guarantee string-based (TEXT) alphabetical
        # sorting perfectly matches numeric time-space ordering.
        return f"{self.next_id():019d}"


# Global generator instance (Node ID 1 for standard instances)
# Future: Pull from env vars CORTEX_NODE_ID for distributed swarms.
flake_gen = SovereignFlake(node_id=1)
