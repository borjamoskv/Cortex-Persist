"""Swarm Heartbeat Monitor — Detects silent daemon thread deaths.

Integrates with the SwarmHeartbeat registry to surface SUSPECT/DEAD
nodes as alerts that flow through the standard daemon pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cortex.swarm.swarm_heartbeat import SWARM_HEARTBEAT, NodeStatus

logger = logging.getLogger("cortex.monitors.swarm_heartbeat")


@dataclass
class HeartbeatAlert:
    """Alert for a daemon thread that missed its heartbeat window."""
    node_id: str
    thread_name: str
    status: str  # "SUSPECT" or "DEAD"
    age_seconds: float
    miss_count: int
    pulse_count: int
    message: str


class SwarmHeartbeatMonitor:
    """Monitor that reaps the SwarmHeartbeat registry on each daemon check cycle."""

    def __init__(self, timeout_seconds: float = 120.0) -> None:
        self._timeout = timeout_seconds

    def check(self) -> list[HeartbeatAlert]:
        """Run the reaper and return alerts for unhealthy nodes."""
        transitioned = SWARM_HEARTBEAT.reap(timeout_seconds=self._timeout)
        alerts: list[HeartbeatAlert] = []

        for node in transitioned:
            severity = "CRITICAL" if node.status == NodeStatus.DEAD else "WARNING"
            alerts.append(HeartbeatAlert(
                node_id=node.node_id,
                thread_name=node.thread_name,
                status=node.status.value,
                age_seconds=node.age_seconds,
                miss_count=node.miss_count,
                pulse_count=node.pulse_count,
                message=(
                    f"💀 [{severity}] Thread '{node.thread_name}' ({node.node_id}) "
                    f"status={node.status.value} — no pulse for {node.age_seconds:.0f}s "
                    f"({node.miss_count} misses, {node.pulse_count} total pulses)"
                ),
            ))

        # Log summary every check
        summary = SWARM_HEARTBEAT.status_summary()
        if transitioned:
            logger.warning("🫀 Heartbeat check: %s", summary)
        else:
            logger.debug("🫀 Heartbeat check: %s", summary)

        return alerts
