import asyncio
import json
import logging

logger = logging.getLogger(__name__)

IPC_SOCKET_PATH = "/tmp/cortex_glial_daemon.sock"

async def dispatch_store_batch(facts: list[dict]) -> dict:
    """Dispatches a store_batch action to the Glial Daemon via Unix Socket."""
    try:
        reader, writer = await asyncio.open_unix_connection(IPC_SOCKET_PATH)
    except ConnectionRefusedError:
        logger.error("Glial Daemon is not running or socket is dead. HARD FAIL (Thermodynamic Apoptosis).")
        raise RuntimeError("Glial Daemon IPC unreachable (Socket refused).")
    except FileNotFoundError:
        logger.error("Glial Daemon socket not found. HARD FAIL.")
        raise RuntimeError("Glial Daemon IPC unreachable (Socket missing).")

    payload = {
        "action": "store_batch",
        "facts": facts
    }
    
    writer.write(json.dumps(payload).encode('utf-8'))
    await writer.drain()
    
    data = await reader.read(10 * 1024 * 1024)
    writer.close()
    await writer.wait_closed()
    
    if data:
        return json.loads(data.decode('utf-8'))
    return {"status": "error", "reason": "Empty response"}
