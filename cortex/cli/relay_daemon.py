import asyncio
import os
from pathlib import Path

import aiofiles
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="CORTEX x Notch Relay")
RELAY_BUFFER = os.path.expanduser("~/.cortex/relay_buffer.jsonl")


def ensure_relay_buffer() -> Path:
    """Create the relay buffer if it does not exist."""
    relay_path = Path(RELAY_BUFFER).expanduser()
    relay_path.parent.mkdir(parents=True, exist_ok=True)
    relay_path.touch(exist_ok=True)
    return relay_path


@app.get("/status")
async def status():
    return {"status": "Sovereign", "buffer": str(ensure_relay_buffer())}


async def event_generator():
    """Polls the relay buffer and yields new events."""
    relay_buffer = await asyncio.to_thread(ensure_relay_buffer)

    # Start at the end of the file
    file_size = await asyncio.to_thread(os.path.getsize, relay_buffer)

    while True:
        current_size = await asyncio.to_thread(os.path.getsize, relay_buffer)
        if current_size > file_size:
            async with aiofiles.open(relay_buffer) as f:
                await f.seek(file_size)
                lines = await f.readlines()
                for line in lines:
                    if line.strip():
                        yield f"data: {line.strip()}\n\n"
            file_size = current_size
        await asyncio.sleep(0.1)


@app.get("/events")
async def events(request: Request):
    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9998)
