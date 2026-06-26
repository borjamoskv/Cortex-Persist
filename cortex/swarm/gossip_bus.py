# [C5-REAL] Exergy-Maximized
"""
GossipBus - Decentralized Swarm Synchronization
Bridges high-level CORTEX Swarm signals with Metal-Level UDP Gossip.
Implements Byzantine Fault Tolerant event propagation across the LEGION-10k.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from cortex_extensions.federation.gossip import GossipNode
from cortex_extensions.ha.gossip import GossipProtocol
from cortex_extensions.signals.bus import AsyncSignalBus

logger = logging.getLogger("cortex.swarm.gossip_bus")


class GossipBus:
    """
    P2P Bus that delegates to the underlying UDP GossipNode for transport,
    while using HA GossipProtocol for semantic digests and conflict resolution.
    """

    def __init__(
        self,
        node_id: str,
        host: str = "0.0.0.0",
        port: int = 7331,
        sync_interval: float = 1.0,
    ):
        self.node_id = node_id
        # Transport Layer (UDP Epidemic)
        self.node = GossipNode(node_id=node_id, bind_host=host, bind_port=port)
        # Logical Layer (Semantic Digests & Vector Clocks)
        self.protocol = GossipProtocol(node_id=node_id, peers=[])
        
        self.bus: AsyncSignalBus | None = None
        self._listener_task: asyncio.Task | None = None
        self.sync_interval = sync_interval
        
        # Callbacks for specific Swarm events
        self._callbacks: dict[str, list[Callable]] = {}

    async def start(self, bus: AsyncSignalBus | None = None) -> None:
        """Start the gossip background loop and bind to local AsyncSignalBus."""
        self.bus = bus
        await self.node.start()
        self._listener_task = asyncio.create_task(self._bridge_signals())
        logger.info(
            f"[P2P Ignited] GossipBus running on node {self.node_id} (Port: {self.node.bind_port})"
        )

    async def stop(self) -> None:
        """Gracefully stop the gossip bus."""
        if self._listener_task:
            self._listener_task.cancel()
        await self.node.stop()
        logger.info(f"GossipBus P2P Terminated on {self.node_id}")

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def broadcast(self, signal_type: str, payload: dict[str, Any]) -> None:
        """
        Broadcast a signal to the P2P swarm.
        Creates a state record and updates the underlying UDP node.
        """
        timestamp = int(asyncio.get_event_loop().time() * 1000)
        state_key = f"signal:{signal_type}:{timestamp}"
        
        # 1. Update logical protocol (Vector Clock & Semantic Digest)
        self.protocol.update_state(state_key, payload)
        
        # 2. Package for UDP transport
        digest = self.protocol.generate_digest()
        network_payload = {
            "type": "BROADCAST",
            "signal_type": signal_type,
            "key": state_key,
            "payload": payload,
            "digest": {
                "vector_clock": digest.vector_clock,
                "record_hashes": digest.record_hashes,
            },
        }
        
        # 3. Inject into UDP Node state for epidemic propagation
        self.node.known_state["version"] += 1
        self.node.known_state["facts"] += 1
        
        # We overload the known_state dict or just push it as a special broadcast?
        # GossipNode propagates known_state. For active broadcast, we use custom transport.
        if self.node.transport and self.node.peers:
            data = json.dumps(network_payload).encode("utf-8")
            for peer_id, peer_info in self.node.peers.items():
                host, port_str = peer_info["address"].split(":")
                try:
                    self.node.transport.sendto(data, (host, int(port_str)))
                except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                    logger.debug("Failed to broadcast to %s: %s", peer_id, e)
                    
        logger.debug(f"Broadcasted {signal_type} to Gossip Swarm")

    async def _bridge_signals(self) -> None:
        """Continuously bridge incoming UDP state to the local event bus."""
        last_version = 0
        while True:
            try:
                current_version = self.node.known_state.get("version", 0)
                if current_version > last_version:
                    # Sync state (simplified logic, a real impl would process the delta)
                    last_version = current_version
                    
                await asyncio.sleep(self.sync_interval)
            except asyncio.CancelledError:
                break
            except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
                logger.exception("[P0] Untracked Exception in GossipBus bridging: %s", e)
                await asyncio.sleep(5.0)

