import asyncio
import os

import aiofiles
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="CORTEX x Notch Relay")
RELAY_BUFFER = os.path.expanduser("~/.cortex/relay_buffer.jsonl")


@app.get("/status")
async def status():
    return {"status": "Sovereign", "buffer": RELAY_BUFFER}


async def event_generator():
    """Polls the relay buffer and yields new events."""
    if not os.path.exists(RELAY_BUFFER):
        os.makedirs(os.path.dirname(RELAY_BUFFER), exist_ok=True)
        async with aiofiles.open(RELAY_BUFFER, "w") as f:
            await f.write("")

    # Start at the end of the file
    file_size = await asyncio.to_thread(os.path.getsize, RELAY_BUFFER)

    while True:
        current_size = await asyncio.to_thread(os.path.getsize, RELAY_BUFFER)
        if current_size > file_size:
            async with aiofiles.open(RELAY_BUFFER) as f:
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
