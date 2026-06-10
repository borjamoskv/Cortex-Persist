# cortex/shannon/env/genesis_env.py
# [C5-REAL] Exergy-Maximized

import asyncio
import random
import secrets
import threading
from typing import Optional, Tuple
from .base import BinaryEnv, StepResult
from .server import MutantServer
from .protocol import GenesisProtocol

class AsyncEnvRunner:
    """
    Background event loop runner to execute asynchronous socket and server
    operations safely from a synchronous interface.
    """
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coro(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def close(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()


class GenesisEnv(BinaryEnv):
    """
    Gymnasium-style environment wrapping the MutantServer with a GenesisProtocol.
    Communication happens over a real TCP loopback interface.
    """
    def __init__(self, host: str = "127.0.0.1", flag: Optional[bytes] = None, seed: Optional[int] = None):
        self.host = host
        self.seed = seed
        self.rng = random.Random(seed)
        
        if flag is not None:
            self.flag = flag
        else:
            if seed is not None:
                flag_hex = f"{self.rng.randint(0, 0xffffffffffffffff):016x}"
                self.flag = f"CORTEX_GENESIS_FLAG_{flag_hex}".encode()
            else:
                self.flag = f"CORTEX_GENESIS_FLAG_{secrets.token_hex(8)}".encode()
        
        self.server: Optional[MutantServer] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.runner = AsyncEnvRunner()

    def _protocol_factory(self) -> GenesisProtocol:
        return GenesisProtocol(flag=self.flag, seed=self.seed)

    async def _async_reset(self) -> bytes:
        await self._async_close_connection()

        if self.server is None:
            self.server = MutantServer(protocol_factory=self._protocol_factory, host=self.host)
            await self.server.start()

        self.reader, self.writer = await asyncio.open_connection(self.server.host, self.server.port)
        # Read the initial challenge (33 bytes)
        challenge = await self.reader.readexactly(33)
        return challenge

    async def _async_step(self, action: bytes) -> StepResult:
        if not self.writer or not self.reader:
            return StepResult(b"", -1.0, True, {"error": "not_connected"})

        try:
            self.writer.write(action)
            await self.writer.drain()

            # Read response (the server sends 4 bytes length then obfuscated flag, or an error string)
            # In general, read whatever bytes are available up to a chunk
            response = await asyncio.wait_for(self.reader.read(1024), timeout=5.0)
            
            # Simple heuristic reward/info parser based on response headers
            done = True
            reward = -1.0
            info = {}

            if response.startswith(b"ERR:"):
                info["error"] = response.decode(errors="replace")
                if response == b"ERR: INVALID_HASH":
                    reward = -10.0
                elif response == b"ERR: INVALID_STRUCT":
                    reward = -5.0
                elif response == b"ERR: BUFFER_TOO_SMALL":
                    reward = -2.0
            else:
                reward = 100.0
                info["success"] = True

            return StepResult(
                observation=response,
                reward=reward,
                done=done,
                info=info
            )
        except Exception as e:
            return StepResult(b"", -1.0, True, {"error": str(e)})

    async def _async_close_connection(self):
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
        self.reader = None

    async def _async_close(self):
        await self._async_close_connection()
        if self.server:
            await self.server.stop()
            self.server = None

    def reset(self) -> bytes:
        return self.runner.run_coro(self._async_reset())

    def step(self, action: bytes) -> StepResult:
        return self.runner.run_coro(self._async_step(action))

    def close(self):
        try:
            self.runner.run_coro(self._async_close())
        finally:
            self.runner.close()
