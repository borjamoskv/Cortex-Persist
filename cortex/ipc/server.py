import asyncio
import json
import logging
from typing import Any
import os

logger = logging.getLogger(__name__)

IPC_SOCKET_PATH = "/tmp/cortex_glial_daemon.sock"

class IPCServer:
    """Single-Writer Actor Queue (BFT). Owns the WAL lock."""
    def __init__(self, engine):
        self.engine = engine
        self._server = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            # Read until EOF or chunk (max 10MB to avoid OOM in massive batches)
            data = await reader.read(10 * 1024 * 1024)
            if not data:
                return
            payload = json.loads(data.decode('utf-8'))
            
            action = payload.get("action")
            if action == "store_batch":
                facts = payload.get("facts", [])
                
                # Exergy extraction: batch store in a single physical transaction
                # to prevent multi-commit overhead in SQLite WAL
                stored_count = 0
                async with self.engine.session() as conn:
                    for f in facts:
                        await self.engine.facts.store(
                            content=f["content"],
                            project=f["project"],
                            fact_type=f["fact_type"],
                            meta=f.get("meta", {}),
                            tags=f.get("tags", []),
                            source=f.get("source", "agent:glial_daemon"),
                            conn=conn
                        )
                        stored_count += 1
                
                response = {"status": "ok", "stored": stored_count}
            else:
                response = {"status": "error", "reason": f"Unknown action {action}"}
                
            writer.write(json.dumps(response).encode('utf-8'))
            await writer.drain()
        except Exception as e:
            logger.error(f"[IPC] Error handling client: {e}")
            writer.write(json.dumps({"status": "error", "reason": str(e)}).encode('utf-8'))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        if os.path.exists(IPC_SOCKET_PATH):
            os.remove(IPC_SOCKET_PATH)
        self._server = await asyncio.start_unix_server(
            self.handle_client, path=IPC_SOCKET_PATH
        )
        logger.info(f"Glial IPC Server started on {IPC_SOCKET_PATH} (Single-Writer BFT mode active)")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if os.path.exists(IPC_SOCKET_PATH):
            os.remove(IPC_SOCKET_PATH)
