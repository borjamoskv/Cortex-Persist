"""
CORTEX V5 - Cables Submarinos
Resilient, asynchronous O(1) TCP communication for the Swarm.
Bypasses intermediate brokers for strict Exergy compliance (Ω₂).
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import itertools
import json
import logging
import time
import zlib
from typing import Any

from cortex.extensions.swarm.protocols import SwarmExtension, SwarmModule
from cortex.extensions.swarm.swarm_heartbeat import SWARM_HEARTBEAT

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
        # Phase 5: Priority queuing for critical signals (Ω₂)
        self._inbox: asyncio.PriorityQueue[tuple[int, int, dict[str, Any]]] | None = None
        self._msg_counter = itertools.count()
        # O(1) Exergy connection pool to avoid TCP handshake overhead
        self._pool: dict[tuple[str, int], tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        # Tracking incoming peers to break infinite readline() blocks on shutdown
        self._active_peers: set[asyncio.StreamWriter] = set()
        # Phase 4: Entropy Shielding
        self._last_sent: dict[int, str] = {}

    async def initialize(self) -> None:
        """Starts the server listener."""
        if self._running:
            return
        self._running = True

        # Lazy initialization couples strictly with the sovereign thread event loop
        if self._inbox is None:
            self._inbox = asyncio.PriorityQueue(maxsize=1000)

        if self.host.startswith("/"):
            self.server = await asyncio.start_unix_server(self._handle_client, path=self.host)
            logger.info("[CablesSubmarinos] Deep trench UDS listener bound to %s", self.host)
        else:
            self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
            logger.info(
                "[CablesSubmarinos] Deep trench TCP listener bound to %s:%d", self.host, self.port
            )

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

                    if "payload" not in msg or "sig" not in msg or "timestamp" not in msg:
                        logger.warning("Malformed transmission dropped (missing critical fields).")
                        continue

                    # Temporal Entropy Shielding (30 second window)
                    timestamp = msg.get("timestamp", 0)
                    if abs(time.time() - timestamp) > 30:
                        logger.warning(
                            "Temporal Entropy rejected: Message drifted outside causal window (Replay Attack)."
                        )
                        continue

                    raw_payload = json.dumps(msg["payload"], sort_keys=True).encode()
                    signable_content = f"{timestamp}:{raw_payload.hex()}".encode()

                    if not self._verify(signable_content, msg["sig"]):
                        logger.warning("Cryptographic verification failed on submarine cable!")
                        continue

                    payload = msg["payload"]
                    SWARM_HEARTBEAT.pulse(node_id=payload.get("author", "submarine_cable"))

                    # Handle Phase 5 Compression
                    if msg.get("compressed"):
                        try:
                            import base64

                            decompressed = zlib.decompress(base64.b64decode(payload["data"]))
                            payload = json.loads(decompressed)
                        except Exception as e:
                            logger.error("Decompression failed: %s", e)
                            continue

                    if self._inbox is not None:
                        priority = msg.get("priority", 5)  # Default priority: balanced
                        await self._inbox.put((priority, next(self._msg_counter), payload))
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

    async def send(
        self,
        target_host: str,
        target_port: int,
        payload: dict[str, Any],
        priority: int = 5,
        compress: bool = False,
    ) -> bool:
        """Transmit over the synchronous backplane using multiplexed pool.

        Args:
            target_host: IP to send to
            target_port: Port to send to
            payload: JSON serializable dict
            priority: 0 (critical) to 9 (telemetry)
            compress: Enable zlib for large payloads
        """
        if not isinstance(payload, dict):
            payload = {"data": payload}

        raw_payload = json.dumps(payload, sort_keys=True).encode()
        timestamp = int(time.time())
        signable_content = f"{timestamp}:{raw_payload.hex()}".encode()

        is_compressed = False
        payload_to_send = payload

        if (
            compress or len(raw_payload) > 1024
        ):  # Check if compression is requested or payload is large
            compressed_payload = zlib.compress(raw_payload, level=zlib.Z_BEST_COMPRESSION)
            payload_to_send = {"data": base64.b64encode(compressed_payload).decode("utf-8")}
            is_compressed = True
        msg_bytes = (
            json.dumps(
                {
                    "payload": payload_to_send,
                    "timestamp": timestamp,
                    "compressed": is_compressed,
                    "priority": priority,
                    "sig": self._sign(signable_content),
                }
            ).encode("utf-8")
            + b"\n"
        )
        target_str = target_host if target_host.startswith("/") else f"{target_host}:{target_port}"
        target = (target_host, target_port)

        # Semaphore/Deduplication check
        if hasattr(self, "_last_sent"):
            payload_hash = hash(frozenset(payload.items()))
            if payload_hash in self._last_sent and self._last_sent[payload_hash] == target_str:
                logger.debug("Deduplication: suppressing identical payload to %s", target_str)
                return True
            self._last_sent[payload_hash] = target_str

        for attempt in range(2):
            try:
                if target not in self._pool:
                    if target_host.startswith("/"):
                        reader, writer = await asyncio.open_unix_connection(target_host)
                    else:
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
        priority, counter, payload = await self._inbox.get()
        return payload
