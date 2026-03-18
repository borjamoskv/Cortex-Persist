"""
CORTEX V5 - Cables Submarinos
Resilient, asynchronous O(1) TCP communication for the Swarm.
Bypasses intermediate brokers for strict Exergy compliance (Ω₂).
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from typing import Any

from cortex.extensions.swarm.protocols import SwarmExtension, SwarmModule

logger = logging.getLogger("cortex.swarm.cables")


class SubmarineCable(SwarmModule, SwarmExtension):
    """
    Direct asynchronous TCP backplane for Swarm telemetry and RPC.
    """

    name = "submarine_cable"

    def __init__(
        self, host: str = "127.0.0.1", port: int = 9999, secret: bytes = b"cortex_default_submarine"
    ):
        self.host = host
        self.port = port
        self.secret = secret
        self.server: asyncio.AbstractServer | None = None
        self._running = False
        # MAXSIZE creates strict TCP backpressure (Ω₂) if the agent loop is overwhelmed
        self._inbox: asyncio.Queue[dict[str, Any]] | None = None
        # O(1) Exergy connection pool to avoid TCP handshake overhead
        self._pool: dict[tuple[str, int], tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        # Tracking incoming peers to break infinite readline() blocks on shutdown
        self._active_peers: set[asyncio.StreamWriter] = set()

    async def initialize(self) -> None:
        """Starts the server listener."""
        if self._running:
            return
        self._running = True

        # Lazy initialization couples strictly with the sovereign thread event loop
        if self._inbox is None:
            self._inbox = asyncio.Queue(maxsize=1000)

        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        logger.info("[CablesSubmarinos] Deep trench listener bound to %s:%d", self.host, self.port)

    async def shutdown(self) -> None:
        """Stops the server listener and severs the link."""
        self._running = False

        # Sever outgoing connections
        for (_, _), (_, w) in list(self._pool.items()):
            w.close()
            try:
                await w.wait_closed()
            except Exception:
                pass
        self._pool.clear()

        # Sever active incoming peers to break blocked readline()
        for w in list(self._active_peers):
            w.close()
            try:
                await w.wait_closed()
            except Exception:
                pass
        self._active_peers.clear()

        # Sever incoming listener
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        logger.info("[CablesSubmarinos] Connection severed.")

    def get_status(self) -> dict[str, Any]:
        """SwarmExtension required protocol."""
        return {
            "module": self.name,
            "status": "active" if self._running else "dormant",
            "host": self.host,
            "port": self.port,
            "inbox_size": self._inbox.qsize() if self._inbox else 0,
            "active_peers": len(self._active_peers),
        }

    def evict_stale_data(self) -> int:
        """Clear the inbox if it's flooded. SwarmExtension compliant."""
        if self._inbox is None:
            return 0

        cleared = 0
        while not self._inbox.empty():
            self._inbox.get_nowait()
            cleared += 1
        return cleared

    def _sign(self, payload: bytes) -> str:
        """Cryptographic HMAC signature for the message."""
        return hmac.new(self.secret, payload, "sha256").hexdigest()

    def _verify(self, payload: bytes, signature: str) -> bool:
        """Cryptographic confirmation."""
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Asynchronous reader for incoming frames."""
        self._active_peers.add(writer)
        try:
            while self._running:
                data = await reader.readline()
                if not data:
                    break

                try:
                    payload_str = data.decode("utf-8").strip()
                    if not payload_str:
                        continue

                    msg = json.loads(payload_str)

                    if "payload" not in msg or "sig" not in msg:
                        logger.warning("Malformed transmission dropped.")
                        continue

                    raw_payload = json.dumps(msg["payload"], sort_keys=True).encode("utf-8")
                    if not self._verify(raw_payload, msg["sig"]):
                        logger.warning("Cryptographic verification failed on submarine cable!")
                        continue

                    if self._inbox is not None:
                        await self._inbox.put(msg["payload"])
                except json.JSONDecodeError:
                    logger.error("Invalid JSON format over submarine cable.")
                except Exception as e:
                    logger.error("Error decoding submarine message: %s", e)
        finally:
            self._active_peers.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def send(self, target_host: str, target_port: int, payload: dict[str, Any]) -> bool:
        """Transmit over the synchronous backplane using multiplexed pool.

        Args:
            target_host: IP to send to
            target_port: Port to send to
            payload: JSON serializable dict

        Returns:
            bool: True if fully transmitted, False otherwise.
        """
        raw_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = self._sign(raw_payload)
        msg_bytes = json.dumps({"payload": payload, "sig": sig}).encode("utf-8") + b"\n"

        target = (target_host, target_port)

        for attempt in range(2):
            try:
                if target not in self._pool:
                    reader, writer = await asyncio.open_connection(target_host, target_port)
                    self._pool[target] = (reader, writer)

                _, writer = self._pool[target]
                logger.debug("Writing %d bytes to %s", len(msg_bytes), target)
                writer.write(msg_bytes)
                await writer.drain()
                logger.debug("Drain complete for %s", target)
                return True
            except (ConnectionError, BrokenPipeError, ConnectionResetError):
                if target in self._pool:
                    _, broken_w = self._pool.pop(target)
                    broken_w.close()
                if attempt == 1:
                    logger.warning(
                        "[CablesSubmarinos] Reaching %s:%d failed. Peer is offline.",
                        target_host,
                        target_port,
                    )
                    return False
        return False

    async def read_next(self) -> dict[str, Any]:
        """Consume the next verified message from the deep trench."""
        if self._inbox is None:
            raise RuntimeError("Cables Submarinos inbox is dormant.")
        return await self._inbox.get()
