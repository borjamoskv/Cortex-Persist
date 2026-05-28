import logging

from fastapi import APIRouter, Depends, HTTPException
from cortex.auth.models import AuthResult
from pydantic import BaseModel, Field
from starlette.requests import Request

from cortex.api.deps import get_async_engine
from cortex.auth import require_permission
from cortex.extensions.swarm.psychohistory import PsychohistoryOrchestrator


async def get_manager(request: Request):
    return request.app.state.swarm_manager


def _tenant_swarm_owners(request: Request) -> dict[str, str]:
    owners = getattr(request.app.state, "swarm_worktree_owners", None)
    if owners is None:
        owners = {}
        request.app.state.swarm_worktree_owners = owners
    return owners


router = APIRouter(prefix="/v1/swarm", tags=["swarm"])

# ── Models ───────────────────────────────────────────────────────────


class WorktreeCreateRequest(BaseModel):
    branch_name: str = Field(..., description="Branch to isolate")
    base_path: str | None = Field(None, description="Optional root for worktrees")


class PsychohistoryRequest(BaseModel):
    scenario_name: str = Field(..., description="The catastrophic scenario to simulate")
    simulated_years: int = Field(
        5, description="Number of years to simulate into the future", ge=1, le=1000
    )
    project: str = Field("SYSTEM", description="Project namespace to save the crystal")


class WorktreeResponse(BaseModel):
    id: str
    branch_name: str
    path: str
    status: str
    created_at: str


class SwarmStatusResponse(BaseModel):
    active_worktrees: int
    total_worktrees: int
    agent_pids: list[int]
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/status", response_model=SwarmStatusResponse)
async def get_swarm_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    manager=Depends(get_manager),
):
    """Aggregate swarm health and load metrics."""
    owners = _tenant_swarm_owners(request)
    managed = [
        w for worktree_id, w in manager.worktrees.items() if owners.get(worktree_id) == auth.tenant_id
    ]
    global_status = await manager.get_status()
    return SwarmStatusResponse(
        active_worktrees=len([w for w in managed if w.status == "active"]),
        total_worktrees=len(managed),
        agent_pids=list({w.pid for w in managed}),
        timestamp=global_status["timestamp"],
    )


@router.post("/worktrees", response_model=WorktreeResponse)
async def create_worktree(
    request: Request,
    req: WorktreeCreateRequest,
    auth: AuthResult = Depends(require_permission("write")),
    manager=Depends(get_manager),
):
    """Provision a new isolated execution environment (Hito 3)."""
    if req.base_path is not None:
        raise HTTPException(
            status_code=422,
            detail="base_path is server-controlled and cannot be set through the public API",
        )

    state = await manager.create_worktree(req.branch_name)
    _tenant_swarm_owners(request)[state.id] = auth.tenant_id
    if state.status == "failed":
        logging.error(
            "Worktree isolation failed for branch %s and path %s", req.branch_name, req.base_path
        )
        raise HTTPException(status_code=500, detail="Worktree isolation failed")

    return WorktreeResponse(
        id=state.id,
        branch_name=state.branch_name,
        path=str(state.path),
        status=state.status,
        created_at=state.created_at,
    )


@router.get("/worktrees/{worktree_id}", response_model=WorktreeResponse)
async def get_worktree_status(
    request: Request,
    worktree_id: str,
    auth: AuthResult = Depends(require_permission("read")),
    manager=Depends(get_manager),
):
    """Get metadata for a specific worktree."""
    if _tenant_swarm_owners(request).get(worktree_id) != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Worktree not found")
    state = await manager.get_worktree(worktree_id)
    if not state:
        raise HTTPException(status_code=404, detail="Worktree not found")

    return WorktreeResponse(
        id=state.id,
        branch_name=state.branch_name,
        path=str(state.path),
        status=state.status,
        created_at=state.created_at,
    )


@router.delete("/worktrees/{worktree_id}")
async def delete_worktree(
    request: Request,
    worktree_id: str,
    auth: AuthResult = Depends(require_permission("admin")),
    manager=Depends(get_manager),
):
    """Cleanly destroy an isolated worktree."""
    owners = _tenant_swarm_owners(request)
    if owners.get(worktree_id) != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Worktree not found")
    success = await manager.delete_worktree(worktree_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worktree not found")
    owners.pop(worktree_id, None)

    return {"status": "tearing_down", "id": worktree_id}


@router.post("/psychohistory")
async def run_psychohistory_simulation(
    req: PsychohistoryRequest,
    auth=Depends(require_permission("admin")),
    engine=Depends(get_async_engine),
):
    """
    Trigger the Psychohistory Fracture Simulator (Hito 4).
    Orchestrates 50 specialized agents using a Semaphore to calculate catastrophic cascades.
    Extracts a Byzantine consensus O(1) Contingency Crystal.
    """
    orchestrator = PsychohistoryOrchestrator(engine)

    try:
        result = await orchestrator.simulate_fracture(
            scenario=req.scenario_name, years=req.simulated_years, project=req.project
        )
        return result
    except Exception as e:
        logging.error("Psychohistory simulation failed: %s", e)
        raise HTTPException(status_code=500, detail="Psychohistory simulation collapsed") from e
