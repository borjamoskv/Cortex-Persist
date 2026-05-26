import asyncio
import time
import os
import subprocess
import shutil
import glob
import re
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import uvicorn
import hashlib
import sys
import struct

# Maintain CORTEX-V3.0 Alignment
sys.path.append(os.path.join(os.path.dirname(__file__), "cortex-core"))
try:
    from persistence import HybridPersistenceManager, enqueue_swarm_task
except ImportError:
    pass

app = FastAPI(title="CORTEX-X100-SSE-ENGINE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cortex_storage = HybridPersistenceManager()
ledger = cortex_storage.l3
vsa = cortex_storage.l2

STATE = {
    "is_running": False,
    "cycle_count": 0,
    "global_yield": 0.0,
    "exergy_ratio": 1.0,
    "vectors": [
        {"id": "bounty", "name": "Code4rena Bounties", "yield": 0.0, "baseline": 2.5},
        {"id": "mev", "name": "LayerZero Fuzz", "yield": 0.0, "baseline": 1.2},
        {
            "id": "millennium",
            "name": "Riemann Singularities ($1M)",
            "yield": 0.0,
            "baseline": 1000.0,
        },
    ],
    "logs": [],
    "agent_states": [0] * 10000,
}


# --- WEBSOCKET BINARY MEMBRANE --- #
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_binary(self, data: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except Exception:
                pass

    async def broadcast_json(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection alive (client can send heartbeats)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def push_state():
    try:
        # 1. Update State
        STATE["global_yield"] = ledger.get_total_yield()
        STATE["cycle_count"] += 1

        # 2. Binary Packaging (Float32Array equivalent)
        # 40,000 bytes fijos para 10,000 agentes
        binary_data = struct.pack("f" * 10000, *STATE["agent_states"])

        # 3. Async Dispatch (Fire and Forget for minimal latency)
        loop = asyncio.get_event_loop()
        loop.create_task(manager.broadcast_binary(binary_data))

        # 4. JSON Dispatch for UI Metadata (SSE compatible)
        events_queue.put_nowait(STATE.copy())
    except Exception:
        pass


def add_log(msg, val):
    STATE["logs"].append({"id": time.time(), "msg": str(msg), "val": str(val)})
    STATE["logs"] = STATE["logs"][-30:]
    push_state()


# --- SSE ENDPOINT --- #
@app.get("/stream")
async def sse_stream():
    async def event_generator():
        while True:
            state_frame = await events_queue.get()
            yield {"data": json.dumps(state_frame)}

    return EventSourceResponse(event_generator())


# --- THE EFFORT MATRIX --- #
EFFORT_MAP = {
    "think": {"fuzz_runs": 256, "swarm_multiplier": 1},
    "think_hard": {"fuzz_runs": 5000, "swarm_multiplier": 10},
    "think_harder": {"fuzz_runs": 15000, "swarm_multiplier": 100},
    "ultrathink": {"fuzz_runs": 31999, "swarm_multiplier": 1000},
}


class FuzzRequest(BaseModel):
    url: str
    effort: str = "think"


@app.post("/trigger_fuzz")
async def trigger_fuzz(req: FuzzRequest):
    if STATE["is_running"]:
        return {"status": "error", "message": "Fuzzer currently running"}
    asyncio.create_task(neuro_static_fuzz(req.url, req.effort))
    return {"status": "accepted", "effort": req.effort, "target": req.url}


# --- THE O(1) FUZZING MEMBRANE --- #
FORGE_WORKSPACE = "/tmp/cortex_x100_fuzz"


class SolidityAnalyzer:
    """Advanced Python-based Solidity AST Pattern Matcher."""

    REENTRANCY_PATTERN = re.compile(r"\.call\{.*?value:.*?\}|msg\.sender\.call")
    ACCESS_PATTERN = re.compile(
        r"function\s+.*?\s+public\s+.*?\{|function\s+.*?\s+external\s+.*?\{"
    )

    @classmethod
    def scan(cls, content):
        results = []
        if cls.REENTRANCY_PATTERN.search(content):
            results.append("POTENTIAL_REENTRANCY")
        if (
            "override" not in content
            and "onlyOwner" not in content
            and cls.ACCESS_PATTERN.search(content)
        ):
            results.append("INSECURE_ACCESS_CONTROL")
        return results


async def neuro_static_fuzz(repo_url: str, effort: str = "think"):
    STATE["is_running"] = True
    effort_cfg = EFFORT_MAP.get(effort, EFFORT_MAP["think"])
    add_log("FORGING CRUCIBLE", f"{FORGE_WORKSPACE} [{effort.upper()}]")

    if os.path.exists(FORGE_WORKSPACE):
        shutil.rmtree(FORGE_WORKSPACE)
    os.makedirs(FORGE_WORKSPACE)

    subprocess.run(
        ["forge", "init", "--force", "--no-git"], cwd=FORGE_WORKSPACE, capture_output=True
    )

    repo_name = repo_url.split("/")[-1]
    add_log("CLONING VECTOR", repo_name)
    target_src = os.path.join(FORGE_WORKSPACE, "src", "target")
    subprocess.run(["git", "clone", "--depth", "1", repo_url, target_src], capture_output=True)

    sol_files = glob.glob(f"{target_src}/**/*.sol", recursive=True)
    add_log("SLITHER-SIM ANALYZER", f"Scanned {len(sol_files)} Contracts")

    for filepath in sol_files:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()
            findings = SolidityAnalyzer.scan(content)
            for fnd in findings:
                add_log("CRITICAL FINDING", fnd)
                # CORTEX-V3.0 Logic: Enqueue specialized task for the Swarm
                effort_cfg = EFFORT_MAP.get(effort, EFFORT_MAP["think"])
                for _ in range(effort_cfg["swarm_multiplier"]):
                    enqueue_swarm_task(
                        agent_name="VulnerabilityFixer",
                        payload={
                            "finding": fnd,
                            "target_file": filepath,
                            "effort": effort,
                            "runs": effort_cfg["fuzz_runs"],
                        },
                    )
                ledger.append(f"Exploit Theory: {fnd}", "bounty", 100.0)
                vsa.record(key=fnd, value=f"Detected in {filepath}")
                push_state()

    # Forge Runtime Phase
    effort_cfg = EFFORT_MAP.get(effort, EFFORT_MAP["think"])
    fuzz_runs_arg = f"--fuzz-runs={effort_cfg['fuzz_runs']}"
    add_log("RUNTIME ENGAGED", f"forge test {fuzz_runs_arg}")
    process = await asyncio.create_subprocess_exec(
        "forge",
        "test",
        "-vv",
        fuzz_runs_arg,
        cwd=FORGE_WORKSPACE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    while True:
        line = await process.stdout.readline()
        if not line:
            break
        line = line.decode("utf-8").strip()
        if "[FAIL]" in line:
            add_log("INVARIANT DESTROYED", line[:50])
            ledger.append("Forge Invariant Break", "mev", 500.0)
            vsa.record(key="Forge FAIL", value=line)
            # Signal swarm for immediate correction
            enqueue_swarm_task(agent_name="InvariantValidator", payload={"log": line})
            push_state()

    await process.wait()
    STATE["is_running"] = False
    add_log("CYCLE COMPLETED", "Swarm Resting")
    push_state()


@app.on_event("startup")
async def startup_event():
    vsa.start_glia()
    asyncio.create_task(vigilia_loop())


async def vigilia_loop():
    target = "https://github.com/lidofinance/lido-dao"
    while True:
        await neuro_static_fuzz(target, "think")
        await asyncio.sleep(60)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
