import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.requests import Request

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine.storage_guard import GuardViolation
from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/v1/engram", tags=["engram"])


class EngramRequest(BaseModel):
    project: str = Field("naroa-2026", min_length=1, max_length=128)
    type: str = Field(..., description="e.g. 'interaction_mark', 'kintsugi_repair'")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Payload data (x, y, size, rot, etc.)"
    )
    source: str | None = Field("naroa-frontend")


class EngramResponse(BaseModel):
    id: int
    project: str
    type: str
    data: dict[str, Any]
    created_at: str


@router.post("", response_model=dict)
async def store_engram(
    req: EngramRequest,
    auth: AuthResult = Depends(require_permission("write")),  # CORTEX handles permissions
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> dict:
    """Cristalización: Store a frontend interaction as an engram in the Sovereign Ledger."""
    try:
        # Convert dictionary to JSON-like string for content since `content` is required in CORTEX facts
        content_str = json.dumps(req.data)

        # We classify this as fact_type matching req.type and give it a tag
        fact_id = await engine.store(
            project=req.project,
            content=content_str,
            tenant_id=auth.tenant_id,
            fact_type=req.type,
            tags=["engram", req.type],
            source=req.source,
            meta=req.data,  # Keep structured data in meta as well
        )
        return {"status": "success", "id": fact_id, "project": req.project}
    except (ValueError, GuardViolation) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        logger.error("Failed to store engram: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal server error while storing engram"
        ) from None


@router.get("", response_model=list[EngramResponse])
async def recall_engrams(
    request: Request,
    project: str = Query("naroa-2026"),
    type: str = Query(..., description="e.g. 'interaction_mark'"),
    limit: int = Query(50, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[EngramResponse]:
    """Absorción: Retrieve collective memory of interactions."""
    _ = request
    try:
        # Recall all memories of this type for the project
        facts = await engine.recall(project=project, tenant_id=auth.tenant_id, limit=limit)

        # Filter by fact_type (assuming engine.recall didn't filter by type natively)
        engrams = []
        for f in facts:
            if f["fact_type"] == type:
                engrams.append(
                    EngramResponse(
                        id=f["id"],
                        project=f["project"],
                        type=f["fact_type"],
                        data=f.get("meta") or {},
                        created_at=f["created_at"],
                    )
                )
                if len(engrams) >= limit:
                    break

        return engrams
    except Exception as e:
        logger.error("Failed to recall engrams: %s", e)
        raise HTTPException(status_code=500, detail="Failed to recall engrams") from e
