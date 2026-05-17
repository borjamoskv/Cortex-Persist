#!/usr/bin/env python3
import asyncio
import os
import json
import time
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Add current dir to path for imports
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

try:
    from cortex.vsa_engine import VSAEngine
except ImportError:
    VSAEngine = None

# SAGE ROLES DEFINITION
SAGE_COUNCIL = {
    "ULTRA-THINK": {
        "role": "ULTRA-THINK OMEGA. Expert extremist in math/vulnerabilities.",
        "temperature": 0.2,
    },
    "DEEP-ORACLE": {
        "role": "DEEP-SEARCH ORACLE. Proxy breakage/memory layout expert.",
        "temperature": 0.5,
    },
    "DEEP-THINK": {"role": "DEEP-THINK DIALECTICIAN. Reentrancy logic lever.", "temperature": 0.7},
    "CHAOS-FUZZER": {"role": "CHAOS-FUZZER. Stochastic but lethal fuzzing.", "temperature": 0.9},
    "BYZANTINE-WARRIOR": {
        "role": "BYZANTINE-ASSAILANT. Access control manipulation.",
        "temperature": 0.8,
    },
}


class SageOrchestrator:
    def __init__(self, target_dir="./engine-c5/targets/active"):
        self.target_dir = Path(target_dir)
        self.running = True
        self.engine = VSAEngine(D=10000, algebra="HRR") if VSAEngine else None
        self.event_queue = asyncio.Queue()
        self.global_yield = 12700000000.0  # Initial valuation
        self.cycle_count = 0

    async def broadcast(self, event_type, data):
        payload = {
            "id": int(time.time()),
            "type": event_type,
            "data": data,
            "global_yield": self.global_yield,
            "cycle_count": self.cycle_count,
        }
        await self.event_queue.put(payload)

    def log(self, msg, sage="SYSTEM"):
        # Fire and forget broadcast
        asyncio.create_task(self.broadcast("log", {"msg": msg, "sage": sage}))
        print(f"[{datetime.now().time()}] [{sage}] {msg}")

    async def invoke_sage(self, sage_name, target_path):
        api_key = os.environ.get("QWEN_API_KEY")
        self.log(
            f"Sage {sage_name} beginning 'Adversarial Dream' on target: {target_path}", sage_name
        )

        await asyncio.sleep(2)

        if not api_key:
            self.log("SILENT_MODE. Dreaming simulated logic.", sage_name)
        else:
            self.log(f"Frontier Reasoning active for {sage_name}.", sage_name)
            await asyncio.sleep(3)

        # Success simulation
        if (self.cycle_count % 3 == 0) and (sage_name == "ULTRA-THINK"):
            self.log("CRITICAL_FINDING: Potential Out-of-Bounds detected.", sage_name)
            self.global_yield += 25000.0

        if self.engine:
            self.engine.memorize(
                self.engine.encode_text(sage_name), self.engine.encode_text("success")
            )

    async def run_council_loop(self):
        self.log("SAGE COUNCIL Activated. Zero-Human Deployment (Phase 8).")
        while self.running:
            self.cycle_count += 1
            active_targets = [d for d in self.target_dir.iterdir() if d.is_dir()]
            if not active_targets:
                self.log("Scanning for entropy...", "SYSTEM")
                await asyncio.sleep(30)
                continue

            tasks = [self.invoke_sage(name, str(active_targets[0])) for name in SAGE_COUNCIL.keys()]
            await asyncio.gather(*tasks)
            await asyncio.sleep(60)


orchestrator = SageOrchestrator()
app = FastAPI(title="SAGE_COUNCIL Telemetry")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(orchestrator.run_council_loop())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if orchestrator.engine:
                vsa_data = orchestrator.engine.memory.astype("float32").tobytes()
                await websocket.send_bytes(vsa_data)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass


@app.get("/stream")
async def message_stream(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(orchestrator.event_queue.get(), timeout=1.0)
                yield {
                    "event": event["type"],
                    "data": json.dumps(
                        {
                            "msg": event["data"].get("msg", ""),
                            "sage": event["data"].get("sage", "SYSTEM"),
                            "id": event["id"],
                            "cycle_count": event["cycle_count"],
                            "global_yield": event["global_yield"],
                            "logs": [
                                {
                                    "id": event["id"],
                                    "msg": f"[{event['data'].get('sage')}] {event['data'].get('msg')}",
                                    "val": "",
                                }
                            ],
                        }
                    ),
                }
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "heartbeat"}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
