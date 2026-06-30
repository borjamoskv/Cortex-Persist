# [C5-REAL] Exergy-Maximized
"""
Multi-node Federation Gossip Protocol (Sovereign Swarm).

Implements the decentralized state-sharing mechanism for CORTEX-Persist clusters.
Allows independent nodes to discover each other, propagate consensus votes,
and maintain global swarm homeostasis without a master node.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any

from babylon60.extensions.swarm.swarm_heartbeat import SWARM_HEARTBEAT

logger = logging.getLogger("babylon60.federation.gossip")


class GossipProtocol(asyncio.DatagramProtocol):
    """UDP Datagram protocol wrapper for GossipNode messages."""

    def __init__(self, node: GossipNode) -> None:
        self.node = node
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        # Spawn handler task to keep receive loop non-blocking
        asyncio.create_task(self.node.handle_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:
        logger.debug("GossipProtocol socket error: %s", exc)


class GossipNode:
    """A sovereign participant in the federated LEGION-10k swarm.

    Executes an epidemic propagation loop to synchronize distributed memory
    without a single point of failure.
    """

    def __init__(
        self,
        node_id: str | None = None,
        bind_host: str = "127.0.0.1",
        bind_port: int = 7331,
    ):
        self.node_id = node_id or f"node_{hex(random.getrandbits(32))[2:]}"
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.peers: dict[str, dict[str, Any]] = {}
        self.known_state: dict[str, Any] = {"version": 0, "facts": 0}
        self._running = False
        self._task: asyncio.Task | None = None
        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: GossipProtocol | None = None

    async def start(self) -> None:
        """Initialize the background gossip propagation loop and UDP server."""
        if self._running:
            return

        self._running = True

        # Bind UDP port for direct node-to-node datagram exchanges
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: GossipProtocol(self),
            local_addr=(self.bind_host, self.bind_port),
        )

        sock = self.transport.get_extra_info("socket")
        if sock:
            self.bind_port = sock.getsockname()[1]

        self._task = asyncio.create_task(self._gossip_loop())
        logger.info(
            f"Gossip Protocol initialized on node {self.node_id} "
            f"listening on {self.bind_host}:{self.bind_port}"
        )

    async def stop(self) -> None:
        """Gracefully terminate the gossip loop and close UDP server."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception as exc:  # noqa: BLE001
                logger.warning("Suppressed exception during task cancel: %s", exc)

        if self.transport:
            self.transport.close()
            self.transport = None
            self.protocol = None

        logger.info(f"Gossip Protocol terminated on node {self.node_id}")

    async def register_peer(self, peer_id: str, address: str) -> None:
        """Register a new peer in the local routing table.

        Args:
            peer_id: Unique identifier of the node.
            address: Network address in format 'host:port'.
        """
        if peer_id == self.node_id:
            return

        self.peers[peer_id] = {
            "address": address,
            "last_seen": time.monotonic(),
            "status": "active",
        }
        logger.debug(f"Peer {peer_id} registered at {address}")

    async def handle_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        """Process incoming gossip UDP packets."""
        try:
            payload = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.debug("Received malformed datagram from %s: %s", addr, e)
            return

        msg_type = payload.get("type")
        sender_id = payload.get("node_id")
        sender_port = payload.get("bind_port")

        if not sender_id or sender_id == self.node_id:
            return

        # Register sender node
        sender_addr = f"{addr[0]}:{sender_port or addr[1]}"
        await self.register_peer(sender_id, sender_addr)

        if "vitals" in payload and sender_id in self.peers:
            self.peers[sender_id]["vitals"] = payload["vitals"]

        # Merge known state
        sender_state = payload.get("known_state", {})
        sender_version = sender_state.get("version", 0)
        sender_facts = sender_state.get("facts", 0)

        if sender_version > self.known_state["version"]:
            self.known_state["version"] = sender_version
            self.known_state["facts"] = max(self.known_state["facts"], sender_facts)
            logger.debug(f"[Gossip] Merged newer state version {sender_version} from {sender_id}")

        # Merge peer table for decentralized discovery
        peer_list = payload.get("peers", {})
        for p_id, p_addr in peer_list.items():
            if p_id != self.node_id and p_id not in self.peers:
                await self.register_peer(p_id, p_addr)

        # Reply if it's a PING
        if msg_type == "PING" and self.transport:
            response = self._build_payload("ACK")
            try:
                self.transport.sendto(response, (addr[0], sender_port or addr[1]))
            except Exception as e:  # noqa: BLE001
                logger.debug("Error sending ACK to %s: %s", addr, e)

    def _build_payload(self, msg_type: str) -> bytes:
        """Format the gossip packet JSON payload."""
        payload = {
            "type": msg_type,
            "node_id": self.node_id,
            "bind_port": self.bind_port,
            "known_state": self.known_state,
            "peers": {p_id: p["address"] for p_id, p in self.peers.items()},
            "vitals": SWARM_HEARTBEAT.status_summary(),
        }
        return json.dumps(payload).encode("utf-8")

    async def _gossip_loop(self) -> None:
        """Background loop to propagate state updates to random peers (Epidemic Protocol)."""
        while self._running:
            try:
                await self._propagate_state()
                # Gossip frequency aligned with LEGION-10k execution speed
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                logger.error(f"Gossip loop networking or runtime error: {e}")
                await asyncio.sleep(1.0)

    async def _propagate_state(self) -> None:
        """Select a random peer and merge states."""
        if not self.peers or not self.transport:
            return

        # Select random peer for epidemic propagation
        peer_id = random.choice(list(self.peers.keys()))
        peer = self.peers[peer_id]

        host, port_str = peer["address"].split(":")
        port = int(port_str)

        # Send PING payload
        payload = self._build_payload("PING")
        try:
            self.transport.sendto(payload, (host, port))
            peer["last_seen"] = time.monotonic()
        except Exception as e:  # noqa: BLE001
            logger.debug("Gossip failed to send PING to peer %s: %s", peer_id, e)
