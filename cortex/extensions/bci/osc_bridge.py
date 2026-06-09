# [C5-REAL] Exergy-Maximized
"""
Aether OSC Bridge (HITO BETA: Consenso Físico)
Connects the Sovereign Cognitive Hypervisor to the physical layer.
Maps Cortex-Persist events (Swarm Consensus, Ledger Mutations) to Open Sound Control (OSC)
datagrams for bidirectional hardware telemetry and sensory actuation.
"""

import asyncio
import logging
from typing import Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_server import AsyncIOOSCUDPServer

logger = logging.getLogger("cortex.bci.osc_bridge")


class AetherOscBridge:
    def __init__(
        self,
        rx_ip: str = "127.0.0.1",
        rx_port: int = 9000,
        tx_ip: str = "127.0.0.1",
        tx_port: int = 9001,
    ):
        self.rx_ip = rx_ip
        self.rx_port = rx_port
        self.tx_ip = tx_ip
        self.tx_port = tx_port

        self.dispatcher = Dispatcher()
        self.dispatcher.map("/cortex/physical/*", self._handle_physical_telemetry)

        self.server: AsyncIOOSCUDPServer | None = None
        self.transport = None
        self.tx_transport = None

    def _handle_physical_telemetry(self, address: str, *args: Any) -> None:
        """Callback for incoming hardware telemetry."""
        logger.info(f"OSC-RX [Physical -> Cortex]: {address} | {args}")
        # In the future, inject this directly into Cortex-Persist Causal Engine

    async def start(self) -> None:
        """Binds the asynchronous OSC server to listen for hardware inputs."""
        loop = asyncio.get_running_loop()
        self.server = AsyncIOOSCUDPServer((self.rx_ip, self.rx_port), self.dispatcher, loop)

        # Start receiver
        self.transport, _ = await self.server.create_serve_endpoint()
        logger.info(f"Aether OSC Bridge RX Bound to udp://{self.rx_ip}:{self.rx_port}")

        # Start generic UDP sender for TX
        class OSCSenderProtocol(asyncio.DatagramProtocol):
            """Protocol for sending OSC messages over UDP."""

        self.tx_transport, _ = await loop.create_datagram_endpoint(
            OSCSenderProtocol, remote_addr=(self.tx_ip, self.tx_port)
        )
        logger.info(f"Aether OSC Bridge TX Ready targeting udp://{self.tx_ip}:{self.tx_port}")

    async def stop(self) -> None:
        if self.transport:
            self.transport.close()
        if self.tx_transport:
            self.tx_transport.close()
        logger.info("Aether OSC Bridge offline.")

    def emit_ledger_mutation(self, tx_id: str, entropy_level: float, source: str) -> None:
        """Converts a SAGA-6 Ledger Mutation into a physical OSC Datagram."""
        if not self.tx_transport:
            logger.warning("OSC Bridge TX not active. Dropping telemetry.")
            return

        msg = OscMessageBuilder(address="/cortex/ledger/mutation")
        msg.add_arg(tx_id)
        msg.add_arg(entropy_level)
        msg.add_arg(source)

        bundle = msg.build()
        self.tx_transport.sendto(bundle.dgram)
        logger.debug(
            f"OSC-TX [Cortex -> Physical]: /cortex/ledger/mutation -> {tx_id} (Entropy: {entropy_level})"
        )

    def emit_swarm_consensus(self, agent_id: str, vote: str, confidence: float) -> None:
        """Emits Byzantine Swarm Votes to the physical layer (e.g. for light sequencing)."""
        if not self.tx_transport:
            return

        msg = OscMessageBuilder(address=f"/cortex/swarm/vote/{agent_id}")
        msg.add_arg(vote)
        msg.add_arg(confidence)

        bundle = msg.build()
        self.tx_transport.sendto(bundle.dgram)
