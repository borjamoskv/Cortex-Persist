import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from cortex.api.deps import get_async_engine
from cortex.auth import require_permission
from cortex.extensions.swarm.psychohistory import PsychohistoryOrchestrator


async def get_manager(request: Request):
    return request.app.state.swarm_manager


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
async def get_swarm_status(auth=Depends(require_permission("read")), manager=Depends(get_manager)):
    """Aggregate swarm health and load metrics."""
    return await manager.get_status()


@router.post("/worktrees", response_model=WorktreeResponse)
async def create_worktree(
    req: WorktreeCreateRequest,
    auth=Depends(require_permission("write")),
    manager=Depends(get_manager),
):
    """Provision a new isolated execution environment (Hito 3)."""
    state = await manager.create_worktree(req.branch_name, req.base_path)
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
    worktree_id: str, auth=Depends(require_permission("read")), manager=Depends(get_manager)
):
    """Get metadata for a specific worktree."""
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
    worktree_id: str, auth=Depends(require_permission("admin")), manager=Depends(get_manager)
):
    """Cleanly destroy an isolated worktree."""
    success = await manager.delete_worktree(worktree_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worktree not found")

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
