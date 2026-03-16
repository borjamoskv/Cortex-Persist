from __future__ import annotations

import asyncio
import socket
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine_async import AsyncCortexEngine


class NetworkVoidOracle:
    def __init__(
        self,
        engine: AsyncCortexEngine,
        poll_interval: float = 300.0,
        check_host: str = "8.8.8.8",
        check_port: int = 53,
        timeout: float = 3.0,
    ) -> None:
        self.engine = engine
        self.poll_interval = poll_interval
        self.check_host = check_host
        self.check_port = check_port
        self.timeout = timeout
        self._running = False
        self._in_void = False
        self._void_start = 0.0

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._ping_reality()
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        await asyncio.sleep(0)

    async def _ping_reality(self) -> None:
        connected = await self._check_connection()

        if not connected and not self._in_void:
            self._in_void = True
            self._void_start = time.time()
            content = (
                "DESCONEXIÓN DEL ENJAMBRE. Entrando en el Vacío (Void State). Aislamiento total."
            )
            if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(self.engine.store):
                await self.engine.store(
                    project="SYSTEM",
                    content=content,
                    fact_type="rule",
                    meta={"oracle": "network_void_v1", "state": "isolated"},
                )
            else:
                self.engine.store_sync(  # type: ignore[type-error]
                    project="SYSTEM",
                    content=content,
                    fact_type="rule",
                    meta={"oracle": "network_void_v1", "state": "isolated"},
                )

        elif connected and self._in_void:
            void_duration = time.time() - self._void_start
            self._in_void = False
            content = f"RECONEXIÓN. Retorno desde el Vacío tras {void_duration:.1f} segundos."

            if hasattr(self.engine, "store") and asyncio.iscoroutinefunction(self.engine.store):
                await self.engine.store(
                    project="SYSTEM",
                    content=content,
                    fact_type="bridge",
                    meta={
                        "oracle": "network_void_v1",
                        "state": "connected",
                        "void_duration_sec": void_duration,
                    },
                )
            else:
                self.engine.store_sync(  # type: ignore[type-error]
                    project="SYSTEM",
                    content=content,
                    fact_type="bridge",
                    meta={
                        "oracle": "network_void_v1",
                        "state": "connected",
                        "void_duration_sec": void_duration,
                    },
                )

    async def _check_connection(self) -> bool:
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._sync_connect)
            return True
        except OSError:
            return False

    def _sync_connect(self) -> None:
        with socket.create_connection(
            (self.check_host, self.check_port), timeout=self.timeout
        ) as s:
            s.recv(1)  # Or just return, the connection success is enough
            return
