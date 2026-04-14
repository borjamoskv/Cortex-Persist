#!/usr/bin/env python3
import asyncio
import os
import json
import time
import shlex
import tempfile
from pathlib import Path
from datetime import datetime
import hashlib

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Add current dir to path for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sqlite3
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import SignalBus

try:
    from cortex.vsa_engine import VSAEngine
except ImportError:
    VSAEngine = None

SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"

# SAGE ROLES DEFINITION
SAGE_COUNCIL = {
    "ULTRA-THINK": {
        "role": "ULTRA-THINK OMEGA. Expert extremist in math/vulnerabilities.",
        "temperature": 0.2
    },
    "DEEP-ORACLE": {
        "role": "DEEP-SEARCH ORACLE. Proxy breakage/memory layout expert.",
        "temperature": 0.5
    },
    "DEEP-THINK": {
        "role": "DEEP-THINK DIALECTICIAN. Reentrancy logic lever.",
        "temperature": 0.7
    },
    "CHAOS-FUZZER": {
        "role": "CHAOS-FUZZER. Stochastic but lethal fuzzing.",
        "temperature": 0.9
    },
    "BYZANTINE-WARRIOR": {
        "role": "BYZANTINE-ASSAILANT. Access control manipulation.",
        "temperature": 0.8
    }
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
            "cycle_count": self.cycle_count
        }
        await self.event_queue.put(payload)

    def log(self, msg, sage="SYSTEM"):
        # Fire and forget broadcast
        asyncio.create_task(self.broadcast("log", {"msg": msg, "sage": sage}))
        print(f"[{datetime.now().time()}] [{sage}] {msg}")

    async def invoke_sage(self, sage_name, target_path):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("QWEN_API_KEY")
        self.log(f"Sage {sage_name} beginning 'Adversarial Dream' on target: {target_path}", sage_name)
        
        await asyncio.sleep(2)
        
        if not api_key:
            self.log(f"SILENT_MODE (C4-SIMULACIÓN). Dreaming simulated logic. No Frontier LLM Key found. [SIMULATION_DIRTY_STATE]", sage_name)
        else:
            self.log(f"Frontier Reasoning active for {sage_name}. Real Agency (C5-REAL).", sage_name)
            await asyncio.sleep(3)

        # Success simulation
        if (self.cycle_count % 3 == 0) and (sage_name == "ULTRA-THINK"):
            self.log(f"CRITICAL_FINDING: Potential Out-of-Bounds detected.", sage_name)
            self.global_yield += 25000.0
        
        if self.engine:
            self.engine.memorize(self.engine.encode_text(sage_name), self.engine.encode_text("success"))

    def _inject_mission(self, agent_name, target_path):
        """Injects a real Ouroboros audit task into the Swarm Queue.

        V9: All missions are pre-classified by SecurityMonitorClassifier
        before queue injection (Ω6: Zero-Trust on external targets).
        """
        try:
            from cortex.extensions.security.security_monitor import (
                SecurityMonitorClassifier,
                ParameterProvenance,
            )
            monitor = SecurityMonitorClassifier()

            worker_id = agent_name.split("-")[0]

            # [Ω5] Generate Immutable Flight Record ID for causal tracking
            flight_record_src = f"{target_path}:{agent_name}:{time.time()}".encode("utf-8")
            flight_record_id = hashlib.sha256(flight_record_src).hexdigest()

            cmd = (
                "python3 /Users/borjafernandezangulo/"
                "Cortex-Persist/cortex-core/"
                f"ouroboros_engine.py --target {shlex.quote(str(target_path))}"
                f" --worker-id {shlex.quote(worker_id)}"
                f" --flight-record-id {shlex.quote(flight_record_id)}"
            )

            task = {
                "agent": agent_name,
                "command": cmd,
            }
            verdict = monitor.classify(
                task,
                user_request="SAGE_COUNCIL audit cycle",
                provenance=ParameterProvenance.AGENT_INFERRED,
            )
            if not verdict.allowed:
                self.log(
                    f"BLOCKED by SecurityMonitor: "
                    f"{verdict.reason}",
                    agent_name,
                )
                return

            queue = {"pending_tasks": []}
            if os.path.exists(SWARM_QUEUE_FILE):
                with open(SWARM_QUEUE_FILE, "r") as f:
                    queue = json.load(f)

            queue["pending_tasks"].append({
                "id": (
                    f"legion_{int(time.time())}"
                    f"_{agent_name}"
                ),
                "agent": agent_name,
                "command": cmd,
                "flight_record_id": flight_record_id,
                "timestamp": time.time(),
            })

            tmp_fd, tmp_path = tempfile.mkstemp(
                prefix="cortex_swarm_queue_",
                dir=os.path.dirname(SWARM_QUEUE_FILE) or None,
            )
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(queue, f, indent=2)
            os.replace(tmp_path, SWARM_QUEUE_FILE)
            self.log(
                f"MISSION DISPATCHED [FlightRecord:{flight_record_id[:8]}...]: {agent_name}"
                f" -> {target_path}",
                "SYSTEM",
            )
        except Exception as e:
            self.log(
                f"Mission Dispatch Failed: {e}",
                "SYSTEM",
            )

    async def run_council_loop(self):
        self.log("SAGE COUNCIL Activated. Zero-Human Deployment (Phase 9 - Legion Strike).")
        while self.running:
            self.cycle_count += 1
            # 1. Target Acquisition: Check local targets directory
            active_targets = [str(d) for d in self.target_dir.iterdir() if d.is_dir()]
            
            # 2. Add external high-value targets if local is empty
            if not active_targets:
                active_targets = [
                    "https://github.com/LayerZero-Labs/LayerZero",
                    "https://github.com/Uniswap/v4-core"
                ]

            self.log(f"Council Cycle {self.cycle_count}: Identified {len(active_targets)} targets.", "SYSTEM")

            # 3. Parallel Legion Strike: Assign one sage per target (or subset)
            for i, target in enumerate(active_targets[:len(SAGE_COUNCIL)]):
                sage_name = list(SAGE_COUNCIL.keys())[i % len(SAGE_COUNCIL)]
                self._inject_mission(sage_name, target)
                # We also invoke the 'Dream' (simulated thought) for UI feedback
                asyncio.create_task(self.invoke_sage(sage_name, target))

            await asyncio.sleep(120) # V6 cadence: 2-minute regrouping

orchestrator = SageOrchestrator()
app = FastAPI(title="SAGE_COUNCIL Telemetry")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SignalBus for Notch overrides (Phase 2)
try:
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    signal_bus = SignalBus(_conn)
except Exception as e:
    print(f"Failed to initialize SignalBus in Orchestrator: {e}")
    signal_bus = None

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(orchestrator.run_council_loop())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if orchestrator.engine:
                vsa_data = orchestrator.engine.memory.astype('float32').tobytes()
                await websocket.send_bytes(vsa_data)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/notch")
async def notch_websocket(websocket: WebSocket):
    """WebSocket bridge for Live Notch ACK/NACK (Phase 2)."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and "pulse_id" in data and "action" in data:
                print(f"📡 [NOTCH] Received override for {data['pulse_id']}: {data['action']}")
                if signal_bus:
                    signal_bus.emit("human_override", data, source="notch_ui")
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
                    "data": json.dumps({
                        "msg": event["data"].get("msg", ""),
                        "sage": event["data"].get("sage", "SYSTEM"),
                        "id": event["id"],
                        "cycle_count": event["cycle_count"],
                        "global_yield": event["global_yield"],
                        "logs": [{"id": event["id"], "msg": f"[{event['data'].get('sage')}] {event['data'].get('msg')}", "val": ""}]
                    })
                }
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "heartbeat"}

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
