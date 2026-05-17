from typing import Optional

"""
CORTEX v5.0 — Mission Orchestration Router.
"""

from fastapi import APIRouter, Depends, Query

from cortex.api.deps import get_engine
from cortex.auth import require_permission
from cortex.engine import CortexEngine
from cortex.extensions.launchpad.main import MissionOrchestrator
from cortex.types.models import MissionLaunchRequest, MissionResponse

__all__ = ["launch_mission", "list_missions"]

router = APIRouter(prefix="/v1/missions", tags=["missions"])


@router.post("/launch", response_model=MissionResponse)
async def launch_mission(
    request: MissionLaunchRequest,
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("write")),
):
    """Launch a new swarm mission through the CORTEX Launchpad."""
    orchestrator = MissionOrchestrator(engine)
    result = orchestrator.launch(
        project=request.project,
        goal=request.goal,
        formation=request.formation,
        agents=request.agents,
    )
    # Sanitize: never expose raw error details to the client
    if result.get("status") == "error" and "error" in result:
        import logging

        logger = logging.getLogger("cortex.routes.missions")
        logger.error("Mission launch failed: %s", result.get("error"))
        result["error"] = "An internal error occurred during mission launch."
    return result


@router.get("/", response_model=list[dict])
async def list_missions(
    project: str | None = Query(None),
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("read")),
):
    """List recent mission intents and reports from the ledger."""
    orchestrator = MissionOrchestrator(engine)
    return orchestrator.list_missions(project=project)
