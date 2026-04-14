import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import EventSourceResponse  # type: ignore[reportAttributeAccessIssue]

app = FastAPI(title="CORTEX Sovereign Relay")

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RELAY_PATH = os.path.expanduser("~/.cortex/relay_buffer.jsonl")


def ensure_relay_buffer() -> Path:
    """Create the relay buffer if it does not exist."""
    relay_path = Path(RELAY_PATH).expanduser()
    relay_path.parent.mkdir(parents=True, exist_ok=True)
    relay_path.touch(exist_ok=True)
    return relay_path


@app.get("/stream")
async def message_stream(request: Request):
    """EventSource endpoint for real-time CORTEX signals."""

    async def event_generator():
        # Open the file and seek to the end
        relay_path = ensure_relay_buffer()

        with relay_path.open() as f:
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

    return EventSourceResponse(event_generator())  # type: ignore[reportArgumentType]


@app.get("/status")
def get_status():
    """Return relay status."""
    return {"status": "ACTIVE", "source": "COTEX-RELAY-V5", "buffer": str(ensure_relay_buffer())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9998)
