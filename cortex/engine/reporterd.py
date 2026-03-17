"""
Sovereign Reporter Daemon — The Event Horizon (Ω-Dynamic SSE).
Empuja telemetría hacia el dashboard en verdadero tiempo real usando
Server-Sent Events (SSE) cada vez que el Manifold emite una señal.
Latencia cero.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import weakref

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import StreamResponse

from cortex.engine.reporter import SovereignReporter

logger = logging.getLogger("cortex.reporterd")


class ManifoldDaemon:
    """Emits live Sovereign System metrics via SSE."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.reporter = SovereignReporter(db_path)
        self.clients: set[weakref.ReferenceType[StreamResponse]] = set()
        self._loop_task: asyncio.Task | None = None

    async def metrics_producer(self):
        """Generates metrics via Event Horizon on DB changes."""
        while True:
            try:
                async for metrics in self.reporter.stream_metrics(interval=0.1):
                    if not self.clients:
                        continue

                    data = json.dumps(metrics.__dict__)

                    dead_clients = set()
                    for client_ref in list(self.clients):
                        client = client_ref()
                        if client is None:
                            dead_clients.add(client_ref)
                            continue
                        client_task = getattr(client, "task", None)
                        if client_task and client_task.done():
                            dead_clients.add(client_ref)
                            continue
                        try:
                            await client.write(f"data: {data}\n\n".encode())
                        except BaseException:  # noqa: BLE001
                            dead_clients.add(client_ref)

                    self.clients -= dead_clients
            except asyncio.CancelledError:
                break
            except (OSError, RuntimeError) as e:
                logger.error("Daemon metric generation error: %s", e)
                await asyncio.sleep(1.0)

    async def sse_handler(self, request: Request) -> StreamResponse:
        """Handles incoming SSE connections from the Live Dashboard."""
        response = StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",  # Permissive for local dashboards
            },
        )
        await response.prepare(request)

        # Send initial connection success
        await response.write(
            b'event: connected\ndata: {"status": "SOVEREIGN_LINK_ESTABLISHED"}\n\n'
        )

        self.clients.add(weakref.ref(response))
        logger.info("New SSE client attached. Total: %d", len(self.clients))

        try:
            # Keep connection open indefinitely
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("SSE client detached.")

        return response

    async def start(self):
        app = web.Application()
        app.router.add_get("/stream", self.sse_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 7070)
        await site.start()

        self._loop_task = asyncio.create_task(self.metrics_producer())
        logger.info("⚡ Sovereign Reporter Daemon active on http://0.0.0.0:7070/stream")

    async def stop(self):
        if self._loop_task:
            self._loop_task.cancel()
        for client_ref in self.clients:
            client = client_ref()
            if client:
                client_task = getattr(client, "task", None)
                if client_task:
                    client_task.cancel()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    daemon = ManifoldDaemon(db_path)
    await daemon.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await daemon.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
