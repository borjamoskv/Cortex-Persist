"""Tests for Hybrid Logical Clock — Phase 4."""

import time

from cortex.sync.hlc import HLCTimestamp, HybridLogicalClock


class TestHLCTimestamp:
    """HLCTimestamp is the compact causal timestamp."""

    def test_ordering(self):
        ts1 = HLCTimestamp(physical_ms=1000, logical=0, node_id=0)
        ts2 = HLCTimestamp(physical_ms=1000, logical=1, node_id=0)
        ts3 = HLCTimestamp(physical_ms=1001, logical=0, node_id=0)
        assert ts1 < ts2 < ts3

    def test_equality(self):
        ts1 = HLCTimestamp(physical_ms=1000, logical=0, node_id=0)
        ts2 = HLCTimestamp(physical_ms=1000, logical=0, node_id=0)
        assert ts1 == ts2

    def test_bytes_roundtrip(self):
        ts = HLCTimestamp(physical_ms=1710000000000, logical=42, node_id=7)
        packed = ts.to_bytes()
        assert len(packed) == 16
        restored = HLCTimestamp.from_bytes(packed)
        assert restored == ts

    def test_string_roundtrip(self):
        ts = HLCTimestamp(physical_ms=1710000000000, logical=255, node_id=3)
        s = ts.to_str()
        restored = HLCTimestamp.from_str(s)
        assert restored == ts

    def test_zero(self):
        z = HLCTimestamp.zero()
        assert z.physical_ms == 0
        assert z.logical == 0
        assert z.node_id == 0


class TestHybridLogicalClock:
    """HLC provides monotonic causal ordering."""

    def test_tick_monotonic(self):
        clock = HybridLogicalClock(node_id=1)
        ts1 = clock.tick()
        ts2 = clock.tick()
        ts3 = clock.tick()
        assert ts1 < ts2 < ts3

    def test_tick_preserves_node_id(self):
        clock = HybridLogicalClock(node_id=42)
        ts = clock.tick()
        assert ts.node_id == 42

    def test_receive_advances_past_remote(self):
        local = HybridLogicalClock(node_id=1)
        # Simulate a remote timestamp far in the future
        remote = HLCTimestamp(
            physical_ms=int(time.time() * 1000) + 10_000_000,
            logical=5,
            node_id=2,
        )
        ts = local.receive(remote)
        assert ts > remote

    def test_receive_same_physical(self):
        local = HybridLogicalClock(node_id=1)
        ts1 = local.tick()
        # Remote has same physical but higher logical
        remote = HLCTimestamp(
            physical_ms=ts1.physical_ms,
            logical=ts1.logical + 10,
            node_id=2,
        )
        ts2 = local.receive(remote)
        assert ts2 > ts1
        assert ts2 > remote

    def test_now_doesnt_advance(self):
        clock = HybridLogicalClock(node_id=0)
        ts1 = clock.tick()
        now = clock.now
        assert now == ts1
        # tick again should advance
        ts2 = clock.tick()
        assert ts2 > now

    def test_reset(self):
        clock = HybridLogicalClock(node_id=0)
        clock.tick()
        clock.reset()
        assert clock.now.physical_ms == 0
        assert clock.now.logical == 0
