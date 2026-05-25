"""NEXUS API Server — FastAPI backend for the Sovereign Agent Directory."""

from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import AgentRegistration, TrustSignalRequest, TaskCreate, TrustSignal
from .registry import AgentRegistry
from .seed import seed_database

DB_PATH = Path(__file__).parent / "nexus.db"
registry: AgentRegistry | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global registry
    registry = AgentRegistry(DB_PATH)
    registry.init_db()
    # Auto-seed if empty
    stats = registry.get_stats()
    if stats.total_agents == 0:
        print("🌑 Empty database — running seed...")
        registry.close()
        seed_database(DB_PATH)
        registry = AgentRegistry(DB_PATH)
        registry.init_db()
    yield
    if registry:
        registry.close()


app = FastAPI(
    title="NEXUS — Sovereign Agent Directory",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _reg() -> AgentRegistry:
    if registry is None:
        raise HTTPException(500, "Registry not initialized")
    return registry


def verify_jules_token(authorization: str | None = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    token = authorization.split(" ", 1)[1]
    if not token.startswith("ya29."):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token layout for Jules")
    return token


# ── Stats ───────────────────────────────────────────────────────


@app.get("/api/stats")
def get_stats():
    return _reg().get_stats().model_dump()


# ── Agents ──────────────────────────────────────────────────────


@app.get("/api/agents")
def list_agents(
    status: str | None = None,
    capability: str | None = None,
    sort: str = "trust",
    limit: int = Query(default=50, le=100),
):
    agents = _reg().list_agents(status=status, capability=capability, sort_by=sort, limit=limit)
    return [a.model_dump() for a in agents]


@app.get("/api/agents/search")
def search_agents(q: str = Query(..., min_length=1)):
    agents = _reg().search_agents(q)
    return [a.model_dump() for a in agents]


@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: str):
    try:
        return _reg().get_agent(agent_id).model_dump()
    except ValueError:
        raise HTTPException(404, "Agent not found")


@app.post("/api/agents/register")
def register_agent(reg: AgentRegistration, token: str = Depends(verify_jules_token)):
    try:
        agent = _reg().register_agent(reg)
        return agent.model_dump()
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/agents/{agent_id}/trust")
def apply_trust(agent_id: str, req: TrustSignalRequest, token: str = Depends(verify_jules_token)):
    try:
        score = _reg().apply_trust_signal(
            agent_id, TrustSignal(req.signal), req.source_agent_id, req.reason
        )
        return score.model_dump()
    except ValueError:
        raise HTTPException(404, "Agent not found")


# ── Tasks ───────────────────────────────────────────────────────


@app.get("/api/tasks")
def list_tasks(status: str | None = None, limit: int = 20):
    tasks = _reg().list_tasks(status=status, limit=limit)
    return [t.model_dump() for t in tasks]


@app.post("/api/tasks")
def create_task(task: TaskCreate, token: str = Depends(verify_jules_token)):
    return _reg().create_task(task).model_dump()


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    try:
        return _reg().get_task(task_id).model_dump()
    except ValueError:
        raise HTTPException(404, "Task not found")


@app.post("/api/tasks/{task_id}/assign/{assignee_id}")
def assign_task(task_id: str, assignee_id: str, token: str = Depends(verify_jules_token)):
    try:
        return _reg().assign_task(task_id, assignee_id).model_dump()
    except ValueError as e:
        raise HTTPException(404 if "not found" in str(e) else 400, str(e))


@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, token: str = Depends(verify_jules_token)):
    try:
        return _reg().complete_task(task_id).model_dump()
    except ValueError as e:
        raise HTTPException(404 if "not found" in str(e) else 400, str(e))


@app.post("/api/tasks/{task_id}/fail")
def fail_task(
    task_id: str, reason: str = Query(default=""), token: str = Depends(verify_jules_token)
):
    try:
        return _reg().fail_task(task_id, reason).model_dump()
    except ValueError as e:
        raise HTTPException(404 if "not found" in str(e) else 400, str(e))


# ── Activity ────────────────────────────────────────────────────


@app.get("/api/activity")
def get_activity(limit: int = Query(default=30, le=100)):
    events = _reg().get_activity(limit=limit)
    return [e.model_dump() for e in events]


# ── Health ──────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    return {"status": "operational", "service": "nexus", "version": "1.0.0"}
