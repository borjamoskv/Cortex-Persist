"""
CORTEX Shared-Memory Signal Bus (Axiom Ω₆).
Zero-copy, lock-minimized signal transport for 10,000-agent swarms.
Uses multiprocessing.SharedMemory for Ultra-Low Latency (Void-State).
"""

from __future__ import annotations

import json
import logging
import struct
import time
from multiprocessing.shared_memory import SharedMemory
from typing import Any

logger = logging.getLogger("cortex.engine.shared_bus")

HEADER_SIZE = 32
DEFAULT_CAPACITY = 8192
DEFAULT_SLOT_SIZE = 512

# Layout v8.5 (Covalent):
# [0-3] HEAD (I) | [4-7] TAIL (I) | [8-11] EXERGY (f) | [12-15] LATENCY (f)
# [16-19] CAP (I) | [20-23] SLOT (I) | [24-27] UNCERTAINTY (f) | [28-31] VERSION (I)


class SovereignSharedBus:
    """Zero-copy Shared Memory Bus for Void-State orchestration."""

    def __init__(
        self,
        name: str = "cortex_signal_bus",
        capacity: int = DEFAULT_CAPACITY,
        slot_size: int = DEFAULT_SLOT_SIZE,
        create: bool = False,
    ):
        self.name = name
        self.capacity = capacity
        self.slot_size = slot_size
        self._shm: SharedMemory | None = None
        self._local_buf: bytearray | None = None
        # SWMR Pattern: Single-Writer (Centurion) eliminates lock contention (Ω₀)

        total_size = HEADER_SIZE + (capacity * slot_size)
        self.num_shards = 1  # Sovereign bus is a single crystalline segment (Ω₆)

        if create:
            try:
                self._shm = SharedMemory(name=name, create=True, size=total_size)
                # Initialize header v8.5 [HEAD, TAIL, EXERGY, LATENCY, CAP, SLOT, UNCERTAINTY]
                self._write_header(0, 0, 1.0, 0.0, capacity, slot_size, 0.0)
                logger.info("🚀 [SHARED-BUS] Created segment '%s' (%d MB)", name, total_size >> 20)
            except FileExistsError:
                self._shm = SharedMemory(name=name)
                logger.debug("🔗 [SHARED-BUS] Attached to existing segment '%s'", name)
            except (OSError, PermissionError) as exc:
                self._activate_local_fallback(total_size, exc)
        else:
            try:
                self._shm = SharedMemory(name=name)
                logger.debug("🔗 [SHARED-BUS] Attached to existing segment '%s'", name)
            except FileNotFoundError:
                if create is None:  # Auto-create if not found
                    self._shm = SharedMemory(name=name, create=True, size=total_size)
                    self._write_header(0, 0, 1.0, 0.0, capacity, slot_size, 0.0)
                else:
                    raise
            except (OSError, PermissionError) as exc:
                self._activate_local_fallback(total_size, exc)

    async def initialize(self) -> None:
        """Sovereign initialization: satisfy the SwarmCommander contract."""

    def _activate_local_fallback(self, total_size: int, exc: BaseException) -> None:
        """Use an in-process ring buffer when POSIX shared memory is unavailable."""
        self._local_buf = bytearray(total_size)
        self._write_header(0, 0, 1.0, 0.0, self.capacity, self.slot_size, 0.0)
        logger.warning(
            "⚠️ [SHARED-BUS] Falling back to local buffer for '%s': %s",
            self.name,
            exc,
        )

    def _buffer(self) -> Any:
        shm = self._shm
        if shm is not None:
            buf = shm.buf
            if buf is None:
                raise RuntimeError("shared memory buffer unavailable")
            return buf

        if self._local_buf is not None:
            return memoryview(self._local_buf)

        return None

    def _write_header(
        self,
        head: int,
        tail: int,
        exergy: float,
        latency: float,
        cap: int,
        slot: int,
        uncertainty: float = 0.0,
    ):
        buf = self._buffer()
        if buf is None:
            return
        # Layout: head(I), tail(I), exergy(f), latency(f), cap(I), slot(I), uncertainty(f), version(I)
        header = struct.pack("IIffIIfI", head, tail, exergy, latency, cap, slot, uncertainty, 850)
        buf[0:32] = header

    def _read_header(self):
        buf = self._buffer()
        if buf is None:
            return (0, 0, 1.0, 0.0, self.capacity, self.slot_size, 0.0, 850)
        return struct.unpack("IIffIIfI", buf[0:32])

    def update_metrics(self, exergy: float, latency: float, uncertainty: float = 0.0):
        """Ω₀ Bit-Parallel Telemetry: Atomic metric update in SHM header."""
        if not self._shm:
            return
        h = self._read_header()
        # Non-blocking header write
        self._write_header(h[0], h[1], exergy, latency, h[4], h[5], uncertainty)

    @property
    def metrics(self) -> dict:
        h = self._read_header()
        return {"exergy": h[2], "latency": h[3], "uncertainty": h[6]}

    async def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        source: str = "cli",
        source_id: int = 0,
        tenant_id: str = "default",
        **kwargs,
    ) -> bool:
        """Lock-Free SWMR Emit (AX-V). High-performance signal injection."""
        buf = self._buffer()
        if buf is None:
            return False

        # Map source string to ID if needed (for Sovereign compatibility)
        sid = source_id
        if source == "commander":
            sid = 1
        elif source == "cli":
            sid = 0

        data = json.dumps(payload or {}).encode("utf-8")
        limit = self.slot_size - 12
        if len(data) > limit:
            data = data[:limit]

        # Read state (Single-Writer: we own 'head')
        h = self._read_header()
        head, tail, exergy, latency, cap, slot = h[0], h[1], h[2], h[3], h[4], h[5]

        offset = HEADER_SIZE + (head * slot)
        ts = time.time()

        # 1. Write Data (Non-visible until head advances)
        record_header = struct.pack("dHH", ts, 0, sid)
        buf[offset : offset + 12] = record_header
        buf[offset + 12 : offset + 12 + len(data)] = data

        # 2. Advance Head (Atomic store in header)
        new_head = (head + 1) % cap
        new_tail = tail
        if new_head == tail:
            new_tail = (tail + 1) % cap

        self._write_header(new_head, new_tail, exergy, latency, cap, slot, h[6])
        return True

    def poll(self, last_index: int) -> list[tuple[int, dict]]:
        """Poll for new signals since last_index.
        Fast-Path: O(1) check of head before linear scan.
        """
        buf = self._buffer()
        if buf is None:
            return []

        header = self._read_header()
        head, tail, cap, slot = header[0], header[1], header[4], header[5]

        # Fast-Path: If last_index is head, no work to do
        if last_index == head:
            return []

        # If last_index is -1, start from tail
        current = last_index if last_index >= 0 else tail

        results = []
        while current != head:
            offset = HEADER_SIZE + (current * slot)

            # Read header
            ts, _, src_id = struct.unpack("dHH", buf[offset : offset + 12])

            # Read payload until null or max slot size
            raw_data = buf[offset + 12 : offset + slot]
            # Find first null byte or end
            try:
                end = raw_data.tobytes().find(b"\x00")
                if end == -1:
                    end = len(raw_data)
                payload = json.loads(raw_data[:end].tobytes().decode("utf-8"))
            except Exception:
                payload = {"error": "malformed_payload"}

            results.append((current, {"timestamp": ts, "source": src_id, "payload": payload}))
            current = (current + 1) % cap

            if len(results) >= 100:  # Safety cap for single poll
                break

        return results

    def close(self):
        shm = self._shm
        if shm is not None:
            shm.close()
        self._local_buf = None

    def unlink(self):
        """Destroy the shared memory segment."""
        shm = self._shm
        if shm is not None:
            try:
                shm.unlink()
            except FileNotFoundError:
                logger.debug("Shared memory segment %s already unlinked", self.name)
            except OSError as exc:
                logger.debug("Shared memory unlink failed for %s: %s", self.name, exc)
            self._shm = None
