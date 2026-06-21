# [C5-REAL] Exergy-Maximized
"""
Triple Identity and Clock Engine for CORTEX Audit System.
Generates cryptographically robust, time-ordered identities for execution events.
"""

import time
import uuid
import threading
from typing import NamedTuple, Optional

# Lamport Clock state
_lamport_clock_lock = threading.Lock()
_lamport_clock = 0

def get_lamport_clock() -> int:
    global _lamport_clock
    with _lamport_clock_lock:
        _lamport_clock += 1
        return _lamport_clock

def update_lamport_clock(received_time: int) -> int:
    global _lamport_clock
    with _lamport_clock_lock:
        _lamport_clock = max(_lamport_clock, received_time) + 1
        return _lamport_clock

def generate_uuidv7() -> str:
    """Generates a UUIDv7 (time-ordered).
    Fallback to UUIDv4 if the python version doesn't support v7 or lacks the library.
    For C5-REAL we emulate v7 prefixing if unavailable natively.
    """
    try:
        # Standard in python 3.14+, uuid7 function is missing in < 3.13 usually
        if hasattr(uuid, "uuid7"):
            return str(uuid.uuid7()) # type: ignore
        else:
            import uuid6
            return str(uuid6.uuid7())
    except ImportError:
        # C5-REAL fallback to a time-prefixed uuid to maintain sortability
        import os
        timestamp_ms = int(time.time() * 1000)
        # 48-bit timestamp
        time_hex = f"{timestamp_ms:012x}"
        random_hex = os.urandom(10).hex()
        # pseudo-v7 layout: 8-4-4-4-12
        return f"{time_hex[:8]}-{time_hex[8:12]}-7{random_hex[:3]}-8{random_hex[3:6]}-{random_hex[6:18]}"

class EventIdentity(NamedTuple):
    event_id: str
    trace_id: str
    span_id: str
    lamport_time: int
    wall_time: float
    monotonic_time: float

def generate_event_identity(trace_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> EventIdentity:
    """Generates the Triple Identity for a new execution event."""
    return EventIdentity(
        event_id=generate_uuidv7(),
        trace_id=trace_id or generate_uuidv7(),
        span_id=generate_uuidv7(),
        lamport_time=get_lamport_clock(),
        wall_time=time.time(),
        monotonic_time=time.monotonic()
    )
