# [C5-REAL] Exergy-Maximized
"""
Swarm Daemon: Python Boundary for Zenoh L3/L4 Transport (Zero-Copy IPC).
"""

from __future__ import annotations

import logging

# Ensure cortex_rs is installed (maturin develop)
try:
    from cortex_rs import ZenohOrchestrator
except ImportError:
    ZenohOrchestrator = None

logger = logging.getLogger(__name__)


class ZenohSwarmDaemon:
    """
    Python wrapper mapping Swarm events down to the native Rust Zenoh Orchestrator.
    Byzantine Boundary: Delegates L3/L4 Transport and ZERO-COPY IPC to Rust.
    """

    def __init__(self, session_id: str, router_endpoint: str = "tcp/localhost:7447"):
        self.session_id = session_id
        self.router_endpoint = router_endpoint

        # Initialize native Rust Substrate for IPC
        try:
            self._rs_orchestrator = ZenohOrchestrator(self.session_id, self.router_endpoint)  # type: ignore
            logger.info(f"[SwarmDaemon] Zenoh Orchestrator Bound: Session {session_id}")
        except Exception as e:
            logger.error(f"[SwarmDaemon] Failed to bind Rust Zenoh Orchestrator: {e}")
            raise

    def publish_belief(self, topic: str, payload_hash: str) -> bool:
        """
        Publishes a payload via Zero-Copy Iceoryx2 shared memory to the Zenoh mesh.
        """
        # Triggers the native C5-REAL execution path
        return self._rs_orchestrator.publish_belief(topic, payload_hash)

    def subscribe_crdt(self, topic_pattern: str) -> bool:
        """
        Subscribes to Semantic CRDT merges in the swarm.
        """
        return self._rs_orchestrator.subscribe_crdt(topic_pattern)
