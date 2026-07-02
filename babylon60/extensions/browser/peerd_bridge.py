# [C5-REAL] Exergy-Maximized
import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("moskv-daemon.peerd")


class PeerdBridgeDaemon:
    """
    Subsystem to bridge BABYLON-60's Sovereign Event Loop with the Peerd browser extension.
    Uses WebSockets to communicate with the browser agent harness.
    """

    def __init__(self, engine: Any, event_bus: Any, host: str = "127.0.0.1", port: int = 8742):
        self.engine = engine
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self._server = None
        self._clients: set = set()
        self._shutdown_event = asyncio.Event()

    async def _handler(self, websocket, path=None):
        logger.info("Browser Agent (Peerd) Connected.")
        self._clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                logger.info(f"Received from Peerd: {data}")

                # Emit to CORTEX event bus
                if self.event_bus:
                    await self.event_bus.publish("browser.task.response", data)

        except Exception as e:
            logger.warning(f"Peerd client disconnected: {e}")
        finally:
            self._clients.remove(websocket)

    async def start(self):
        try:
            import websockets

            logger.info(f"🌐 Starting PeerdBridge WebSocket Server on ws://{self.host}:{self.port}")
            self._server = await websockets.serve(self._handler, self.host, self.port)
            await self._shutdown_event.wait()
        except ImportError:
            logger.error("websockets package not found. Cannot start PeerdBridgeDaemon.")
        except Exception as e:
            logger.error(f"Failed to start PeerdBridgeDaemon: {e}")

    async def stop(self):
        logger.info("Stopping PeerdBridgeDaemon...")
        self._shutdown_event.set()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
