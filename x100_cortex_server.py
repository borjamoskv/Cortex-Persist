import asyncio
import time
import os
import subprocess
import shutil
import glob
import re
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn
import hashlib
import sys

# Integrate persistence logic
sys.path.append(os.path.join(os.path.dirname(__file__), "cortex-core"))
try:
    from persistence import LedgerManager, VSAMemory
except ImportError:
    # Handle if path differs
    pass

app = FastAPI(title="CORTEX-X100-SSE-ENGINE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ledger = LedgerManager()
vsa = VSAMemory()

STATE = {
    "is_running": False,
    "cycle_count": 0,
    "global_yield": 0.0,
    "exergy_ratio": 1.0,
    "vectors": [
        {"id": 'bounty', "name": 'Code4rena Bounties', "yield": 0.0, "baseline": 2.5},
        {"id": 'mev', "name": 'LayerZero Fuzz', "yield": 0.0, "baseline": 1.2},
        {"id": 'millennium', "name": 'Riemann Singularities ($1M)', "yield": 0.0, "baseline": 1000.0},
    ],
    "logs": [],
    "agent_states": [0] * 10000 
}

events_queue = asyncio.Queue()

def push_state():
    try:
        # Update yields from ledger persistent state
        l_state = ledger._load_state()
        total = sum(l["yield_amount"] for l in l_state.get("ledgers", []))
        STATE["global_yield"] = total
        # Update vector yields
        for v in STATE["vectors"]:
            v["yield"] = sum(l["yield_amount"] for l in l_state.get("ledgers", []) if l["vector_id"] == v["id"])
            
        events_queue.put_nowait(STATE.copy())
    except asyncio.QueueFull:
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

# --- THE CORTEX X100 ENGINE (C5-REAL) --- #
FORGE_WORKSPACE = "/tmp/cortex_x100_fuzz"

class SolidityAnalyzer:
    """Advanced Python-based Solidity AST Pattern Matcher."""
    REENTRANCY_PATTERN = re.compile(r'\.call\{.*?value:.*?\}|msg\.sender\.call')
    ACCESS_PATTERN = re.compile(r'function\s+.*?\s+public\s+.*?\{|function\s+.*?\s+external\s+.*?\{')

    @classmethod
    def scan(cls, content):
        results = []
        if cls.REENTRANCY_PATTERN.search(content):
            results.append("POTENTIAL_REENTRANCY")
        if "override" not in content and "onlyOwner" not in content and cls.ACCESS_PATTERN.search(content):
            results.append("INSECURE_ACCESS_CONTROL")
        return results

async def neuro_static_fuzz(repo_url: str):
    STATE["is_running"] = True
    add_log("FORGING CRUCIBLE", FORGE_WORKSPACE)
    
    if os.path.exists(FORGE_WORKSPACE):
        shutil.rmtree(FORGE_WORKSPACE)
    os.makedirs(FORGE_WORKSPACE)
    
    subprocess.run(["forge", "init", "--force", "--no-git"], cwd=FORGE_WORKSPACE, capture_output=True)
    
    repo_name = repo_url.split("/")[-1]
    add_log("CLONING VECTOR", repo_name)
    target_src = os.path.join(FORGE_WORKSPACE, "src", "target")
    subprocess.run(["git", "clone", "--depth", "1", repo_url, target_src], capture_output=True)

    sol_files = glob.glob(f"{target_src}/**/*.sol", recursive=True)
    add_log("SLITHER-SIM ANALYZER", f"Scanned {len(sol_files)} Contracts")

    for filepath in sol_files:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            findings = SolidityAnalyzer.scan(content)
            for fnd in findings:
                add_log("CRITICAL FINDING", fnd)
                yield_val = 100.0 if fnd == "POTENTIAL_REENTRANCY" else 50.0
                ledger.append(f"Exploit Theory: {fnd}", "bounty", yield_val)
                vsa.record(f"exploit:{fnd}", filepath)
                push_state()

    # Forge Runtime Phase
    add_log("RUNTIME ENGAGED", "forge test")
    process = await asyncio.create_subprocess_exec(
        "forge", "test", "-vv",
        cwd=FORGE_WORKSPACE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    while True:
        line = await process.stdout.readline()
        if not line: break
        line = line.decode('utf-8').strip()
        if "[FAIL]" in line:
            add_log("INVARIANT DESTROYED", line[:50])
            ledger.append("Forge Invariant Break", "mev", 500.0)
            vsa.record("forge:fail", line)
            push_state()
        elif "[PASS]" in line:
            STATE["cycle_count"] += 1
            if STATE["cycle_count"] % 10 == 0:
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
        await neuro_static_fuzz(target)
        await asyncio.sleep(60)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
