# [C5-REAL] Exergy-Maximized
import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cortex import __version__
from cortex.engine.bifurcation_engine import ExergyBifurcationEngine
from cortex.engine.causal_scheduler import CausalScheduler
from cortex.engine.entropy_daemon import EntropyDaemon
from cortex.engine.exergy_daemon import ExergyDaemon
from cortex.engine.rollback_engine import CausalRollbackEngine
from cortex.ledger.causal_graph import CausalGraph
from cortex.ledger.execution_trace import ExecutionTraceLedger

CORTEX_DB_PATH = os.getenv(
    "CORTEX_DB_PATH",
    (
        "/tmp/cortex_engine.db"
        if os.getenv("VERCEL")
        else str(Path("~/.cortex/cortex_engine.db").expanduser())
    ),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización del ecosistema termodinámico
    Path(CORTEX_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    ledger = ExecutionTraceLedger(CORTEX_DB_PATH)
    graph = CausalGraph(CORTEX_DB_PATH)
    rollback = CausalRollbackEngine(CORTEX_DB_PATH, ledger, None)
    scheduler = CausalScheduler(graph, rollback, ledger)
    bifurcation = ExergyBifurcationEngine(ledger, scheduler)

    async with aiosqlite.connect(CORTEX_DB_PATH) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_trace_ledger (
                id              TEXT PRIMARY KEY,
                tenant_id       TEXT NOT NULL DEFAULT 'default',
                origin          TEXT NOT NULL,
                cost            REAL NOT NULL,
                lineage         TEXT NOT NULL DEFAULT '[]',
                outcome         TEXT NOT NULL,
                rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS thermodynamics_state (tenant_id TEXT PRIMARY KEY, entropy_budget REAL)"
        )
        await conn.commit()

    exergy_daemon = ExergyDaemon(bifurcation, scan_interval=60.0)
    entropy_daemon = EntropyDaemon(CORTEX_DB_PATH, scan_interval=3600.0)

    exergy_daemon.start()
    entropy_daemon.start()

    yield

    await exergy_daemon.stop()
    await entropy_daemon.stop()


app = FastAPI(
    title="CORTEX Persist API",
    description="Motor C5-REAL para visualización de exergía y purga de influencers.",
    version=__version__,
    lifespan=lifespan,
)

# CORS para permitir peticiones desde cortexpersist.com (o localhost para dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Reemplazar con dominios específicos en C5-REAL prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GUARD_DB_PATH = Path("~/.cortex/influencer_guard.db").expanduser()
SCRAPER_DB_PATH = "influencer_audit_v1.db"


class StrikeInfo(BaseModel):
    influencer_name: str
    strikes: int
    status: str
    last_update: float


class AuditLogEntry(BaseModel):
    prompt: str
    response: str
    hallucinated: bool
    reason: str
    timestamp: float


@app.get("/api/v1/health")
async def health_check():
    """Terminal de estado C5-REAL."""
    return {"status": "ONLINE", "exergy": "MAX", "db_guard": GUARD_DB_PATH.exists()}


@app.get("/api/v1/influencers", response_model=list[StrikeInfo])
async def get_all_influencers():
    """Retorna el estado del radar del Influencer Guard."""
    if not GUARD_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Guard DB not found. No telemetry yet.")

    async with aiosqlite.connect(GUARD_DB_PATH) as conn:
        async with conn.execute(
            "SELECT influencer_name, strikes, status, last_update FROM influencer_strikes ORDER BY strikes DESC"
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        StrikeInfo(influencer_name=r[0], strikes=r[1], status=r[2], last_update=r[3]) for r in rows
    ]


@app.get("/api/v1/influencers/{name}/audit", response_model=list[AuditLogEntry])
async def get_influencer_audit(name: str):
    """Extrae el log criptográfico de alucinaciones (las pruebas del delito)."""
    if not GUARD_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Guard DB not found.")

    async with aiosqlite.connect(GUARD_DB_PATH) as conn:
        async with conn.execute(
            "SELECT prompt, response, hallucinated, reason, timestamp FROM audit_log WHERE influencer_name = ? ORDER BY timestamp DESC",
            (name,),
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        AuditLogEntry(
            prompt=r[0], response=r[1], hallucinated=bool(r[2]), reason=r[3], timestamp=r[4]
        )
        for r in rows
    ]


@app.get("/api/v1/toxic_community", response_model=list[dict[str, Any]])
async def get_toxic_community_events(limit: int = 50):
    """Extrae los últimos hits del motor de extracción asíncrona de comentarios (Vector Alpha)."""
    db_path = Path(SCRAPER_DB_PATH)
    if not db_path.exists():
        return []

    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute(
            "SELECT video_id, target_id, taxonomia_ataque, cita_textual_exacta FROM eventos_acoso LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        {"video_id": r[0], "target_id": r[1], "taxonomia_ataque": r[2], "cita": r[3]} for r in rows
    ]


@app.websocket("/api/v1/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Generate dummy telemetry matching LEGIØN-10000 format
            frame_nodes = []
            for _ in range(50):
                frame_nodes.append(
                    {
                        "x": random.randint(0, 1000),
                        "y": random.randint(0, 1000),
                        "z": random.random() * 3.14159 * 2,
                        "entropy": random.random(),
                        "target": random.choice([None, "toxic_node", "anomaly"]),
                    }
                )

            payload = {"type": "FRAME", "timestamp": time.time(), "data": frame_nodes}

            await websocket.send_json(payload)
            await asyncio.sleep(0.1)  # 10fps broadcast
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
