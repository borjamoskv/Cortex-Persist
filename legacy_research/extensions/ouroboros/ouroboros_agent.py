"""
CORTEX-PERSIST: Ouroboros Node Keeper MVP
Loop asíncrono y exposición del API REST de salud. Orquesta el ciclo de vida continuo cada 60s.
"""
import asyncio
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from legacy_research.extensions.ouroboros_mythos.ouroboros_loop import MythosOuroborosEngine

app = FastAPI(title="Ouroboros Node Keeper")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ouroboros")

# Sovereign Mythos Engine Instance
engine = MythosOuroborosEngine()

@app.get("/health")
def read_health():
    health_score = engine.meta_controller.health_score
    status = "healthy" if health_score >= 9850 else "degraded"
    return {
        "status": status,
        "health_score": health_score,
        "active_version": engine.meta_controller.active_version,
        "cycle_count": engine.state.cycle_count,
        "state_hash": hex(engine.state.state_hash),
        "identity_anchor": engine.state.identity_anchor.decode("utf-8")
    }

@app.get("/metrics")
def read_metrics():
    return {
        "total_microjoules": engine.exergy.total_microjoules,
        "current_exergy_score": engine.exergy.current_score(),
        "temperature_mc": engine.exergy._read_temperature_mc(),
    }

@app.get("/dashboard", response_class=HTMLResponse)
def read_dashboard():
    log_path = engine.ledger.log_path
    events = []
    import json
    import os
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception:
            pass

    events.reverse()
    
    rows = "".join([f"<tr><td>{e.get('timestamp')}</td><td>{e.get('type')}</td><td>{e.get('hash')[:8] if e.get('hash') else '-'}</td><td>{e.get('payload', {})}</td></tr>" for e in events])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ouroboros Mythos Dashboard</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #0A0A0A; color: #E0E0E0; margin: 2rem; }}
            h1, h2 {{ color: #2B3BE5; font-weight: normal; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 0.9rem; }}
            th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #333; }}
            th {{ background: #111; color: #888; font-weight: 500; text-transform: uppercase; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .metric {{ display: inline-block; padding: 1rem; background: #111; border-left: 4px solid #2B3BE5; margin-right: 1rem; margin-bottom: 1rem; min-width: 150px; }}
            .metric .label {{ color: #888; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.5rem; }}
            .metric .value {{ font-size: 1.5rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>OUROBOROS KERNEL (Phase 2)</h1>
            
            <div style="display: flex; flex-wrap: wrap;">
                <div class="metric"><div class="label">Status</div><div class="value">{"HEALTHY" if engine.meta_controller.health_score >= 9850 else "DEGRADED"}</div></div>
                <div class="metric"><div class="label">Health Score</div><div class="value">{engine.meta_controller.health_score}</div></div>
                <div class="metric"><div class="label">Active Version</div><div class="value">{engine.meta_controller.active_version}</div></div>
                <div class="metric"><div class="label">Cycles</div><div class="value">{engine.state.cycle_count}</div></div>
            </div>

            <h2>Execution Ledger (Recent Events)</h2>
            <table>
                <tr><th>Timestamp</th><th>Event Type</th><th>Hash</th><th>Payload</th></tr>
                {rows if rows else "<tr><td colspan='4'>No data yet. Waiting for cycle.</td></tr>"}
            </table>
        </div>
    </body>
    </html>
    """
    return html

@app.get("/ledger")
def read_ledger():
    log_path = engine.ledger.log_path
    events = []
    import json
    import os
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read ledger: {e}")
    return {"log_path": log_path, "events": events}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Ouroboros Mythos Engine background task...")
    asyncio.create_task(engine.run_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
