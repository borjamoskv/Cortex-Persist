# cortex/shannon/env/server.py
# [C5-REAL] Exergy-Maximized

import asyncio
import logging
from collections.abc import Callable

from .protocol import BinaryProtocol

logger = logging.getLogger(__name__)


class MutantServer:
    """
    Protocol-agnostic TCP server that spins up a custom BinaryProtocol per connection.
    """

    def __init__(
        self, protocol_factory: Callable[[], BinaryProtocol], host: str = "127.0.0.1", port: int = 0
    ):
        self.protocol_factory = protocol_factory
        self.host = host
        self.port = port
        self.server: asyncio.AbstractServer | None = None
        self._running = False

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        protocol = self.protocol_factory()
        try:
            # 1. Send Handshake Challenge
            challenge = protocol.get_challenge()
            writer.write(challenge)
            await writer.drain()

            # 2. Read Client Response
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            except asyncio.TimeoutError:
                return

            if not data:
                return

            response_bytes, reward, done, info = protocol.handle_message(data)
            writer.write(response_bytes)
            await writer.drain()
        except Exception as e:
            logger.debug(f"MutantServer connection error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        self.port = self.server.sockets[0].getsockname()[1]
        self._running = True
        logger.info(f"MutantServer started on {self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self._running = False
