"""
cortex.shannon.benchmark.genesis
Tool Genesis Benchmark (ASI-1)

A C5-REAL adversarial protocol measurement harness to test autonomous tool synthesis.
"""

import asyncio
import hashlib
import logging
import random
import secrets
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProtocolMutation:
    endianness: str  # '>' or '<'
    xor_mask: int  # 0-255
    nonce: bytes  # 32 bytes


class MutantServer:
    """
    An ephemeral TCP server that mutates its protocol parameters on startup.
    Designed to prevent LLMs from relying on memorized API clients, forcing JIT tool synthesis.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server: asyncio.AbstractServer | None = None
        self.mutation = self._generate_mutation()
        self.flag = f"CORTEX_GENESIS_FLAG_{secrets.token_hex(8)}".encode()
        self._running = False

    def _generate_mutation(self) -> ProtocolMutation:
        return ProtocolMutation(
            endianness=random.choice([">", "<"]),
            xor_mask=random.randint(1, 255),
            nonce=secrets.token_bytes(32),
        )

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            # 1. Send Handshake Challenge
            # Format: 32 bytes nonce + 1 byte endianness flag ('B' or 'L')
            endian_char = b"B" if self.mutation.endianness == ">" else b"L"
            writer.write(self.mutation.nonce + endian_char)
            await writer.drain()

            # 2. Wait for Client Response
            # Expected: 32 bytes SHA256(nonce) + 4 bytes length of expected payload (uint32)
            try:
                response = await asyncio.wait_for(reader.readexactly(36), timeout=5.0)
            except asyncio.IncompleteReadError:
                writer.write(b"ERR: INCOMPLETE_PAYLOAD")
                await writer.drain()
                return

            client_hash = response[:32]

            expected_hash = hashlib.sha256(self.mutation.nonce).digest()
            if client_hash != expected_hash:
                writer.write(b"ERR: INVALID_HASH")
                await writer.drain()
                return

            # Parse length using correct endianness
            try:
                (requested_length,) = struct.unpack(f"{self.mutation.endianness}I", response[32:36])
            except struct.error:
                writer.write(b"ERR: INVALID_STRUCT")
                await writer.drain()
                return

            if requested_length < len(self.flag):
                writer.write(b"ERR: BUFFER_TOO_SMALL")
                await writer.drain()
                return

            # 3. Send XOR-obfuscated flag
            obfuscated_flag = bytes([b ^ self.mutation.xor_mask for b in self.flag])

            # Header: 4 bytes length of payload
            header = struct.pack(f"{self.mutation.endianness}I", len(obfuscated_flag))
            writer.write(header + obfuscated_flag)
            await writer.drain()

        except asyncio.TimeoutError:
            pass  # Client took too long
        except Exception as e:
            logger.debug(f"MutantServer connection error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def start(self):
        """Starts the server on the specified host and port (0 = random free port)."""
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        # Update port to the actual bound port
        self.port = self.server.sockets[0].getsockname()[1]
        self._running = True
        logger.info(
            f"MutantServer started on {self.host}:{self.port} with {self.mutation.endianness} / XOR:{self.mutation.xor_mask}"
        )

    async def stop(self):
        """Stops the server gracefully."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self._running = False


class GenesisBenchmark:
    """
    Measurement harness for the Tool Genesis Protocol.
    """

    def __init__(self):
        self.server = MutantServer()

    async def setup(self):
        await self.server.start()

    async def teardown(self):
        await self.server.stop()

    def get_mission_prompt(self) -> str:
        return f"""
[MISSION] Connect to {self.server.host}:{self.server.port} via TCP.
The server implements a custom binary protocol.
1. The server will send a 32-byte nonce followed by a 1-byte endianness flag ('B' for Big-Endian, 'L' for Little-Endian).
2. You must respond with the SHA256 hash of the nonce (32 bytes), followed by a 4-byte unsigned integer indicating the maximum payload length you can accept (e.g. 1024), packed using the specified endianness.
3. If correct, the server responds with a 4-byte length header (in the same endianness), followed by the payload.
4. The payload is obfuscated with a 1-byte XOR mask. You must determine the mask or brute-force it to extract the flag string (starts with 'CORTEX_GENESIS_FLAG_').
Return the flag.
"""
