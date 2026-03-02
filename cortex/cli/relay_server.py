import asyncio
import json
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import EventSourceResponse

app = FastAPI(title="CORTEX Sovereign Relay")

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RELAY_PATH = os.path.expanduser("~/.cortex/relay_buffer.jsonl")


@app.get("/stream")
async def message_stream(request: Request):
    """EventSource endpoint for real-time CORTEX signals."""

    async def event_generator():
        # Open the file and seek to the end
        if not os.path.exists(RELAY_PATH):
            with open(RELAY_PATH, "w") as f:
                pass

        with open(RELAY_PATH) as f:
            f.seek(0, os.SEEK_END)
            while True:
                if await request.is_disconnected():
                    break

                line = f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    event = json.loads(line)
                    yield {"event": "message", "data": json.dumps(event)}
                except (json.JSONDecodeError, ValueError):
                    continue

    return EventSourceResponse(event_generator())


@app.get("/status")
def get_status():
    """Return relay status."""
    return {"status": "ACTIVE", "source": "COTEX-RELAY-V5"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9998)
