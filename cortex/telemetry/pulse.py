# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX v6.0 — Pulse-Driven Observability (Ω₄: Aesthetic Integrity).

True observability operates on the pulse (SignalBus) instead of the corpse (post-hoc logs).
This module provides a sovereign registry that derives system metrics directly from
L1 consciousness signals.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.signals.bus import SignalBus

logger = logging.getLogger("cortex.telemetry.pulse")


@dataclass(slots=True)
class PulseMetric:
    """A metric derived from the system pulse."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)
    source: str = "pulse"


class PulseRegistry:
    """Sovereign Metrics Registry driven by the SignalBus pulse.

    Redesigns the data flow by preferring direct signals over manual increments.
    """

    def __init__(self, signal_bus: SignalBus | None = None) -> None:
        self._signal_bus = signal_bus
        self._metrics: dict[str, PulseMetric] = {}
        self._lock = threading.RLock()
        self._ghost_metrics: set[str] = set()  # Metrics flagged as "shadows"
        self._is_active = False

    def set_bus(self, signal_bus: SignalBus) -> None:
        """Inject the SignalBus pulse source."""
        self._signal_bus = signal_bus

    async def start_observer(self, interval: float = 1.0) -> None:
        """Starts the pulse observer loop."""
        if self._is_active or not self._signal_bus:
            return
        self._is_active = True
        logger.info("💓 [PULSE] Observer ignited. Redesigning data flow to reality.")

        while self._is_active:
            try:
                # Poll L1 signals
                signals = self._signal_bus.poll(consumer="pulse_observer", limit=100)
                if signals:
                    with self._lock:
                        for signal in signals:
                            self._process_signal(signal)
            except Exception as e:
                logger.error("[PULSE] Pulse scan failed: %s", e)
            await asyncio.sleep(interval)

    def _process_signal(self, signal: Any) -> None:
        """Infers metrics from a pulse signal."""
        event_type = signal.event_type

        # 1. Automatic metric derivation from event_type
        # Patterns:
        #   'error:*' -> counter
        #   'heartbeat:*' -> gauge
        #   'consensus:*' -> counter

        if event_type.startswith("error:"):
            metric_name = f"cortex_{event_type.replace(':', '_')}_total"
            self.inc(metric_name, labels={"source": signal.source})
        elif event_type == "heartbeat:pulse":
            drift = signal.payload.get("semantic_drift", 0.0)
            self.set_gauge("cortex_semantic_drift", drift)
        elif event_type.startswith("consensus:"):
            self.inc("cortex_consensus_ops_total", labels={"op": event_type.split(":")[1]})

        # 2. Shadow Detection: If we see a signal for something that was manually logged,
        # we flag the manual log as a "ghost".
        self._ghost_metrics.add(event_type)

    def inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increments a pulse-driven counter."""
        key = self._gen_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = PulseMetric(name=name, labels=labels or {})
            self._metrics[key].value += value
            self._metrics[key].last_update = time.time()

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Sets a pulse-driven gauge."""
        key = self._gen_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = PulseMetric(name=name, labels=labels or {})
            self._metrics[key].value = value
            self._metrics[key].last_update = time.time()

    def _gen_key(self, name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        l_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{l_str}}}"

    def get_pulse(self) -> dict[str, Any]:
        """Returns the current state of the pulse."""
        with self._lock:
            return {
                "active_metrics": len(self._metrics),
                "shadow_ghosts": list(self._ghost_metrics),
                "pulse_rate": sum(
                    1 for m in self._metrics.values() if time.time() - m.last_update < 60
                ),
            }


# Global Pulse Registry (v6)
PULSE = PulseRegistry()
