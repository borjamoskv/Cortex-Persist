# [C5-REAL] Exergy-Maximized
"""
Benchmark Router.
API endpoints for managing the CORTEX IA Hype Benchmark dataset.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.types.models import StoreResponse

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/v1/benchmark", tags=["benchmark"])


class InfluencerIngestRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    handle: str = Field(..., min_length=1, max_length=64)
    category: str = Field(..., min_length=1, max_length=64)
    hype: int = Field(..., ge=0, le=100)
    utility: int = Field(..., ge=0, le=100)
    followers: int = Field(..., ge=0)
    cliche: str = Field(..., min_length=1, max_length=1024)
    verdict: str = Field(..., min_length=1, max_length=1024)
    territory: str = Field("ES", min_length=2, max_length=10)
    reality_level: str = Field("C4-SINTÉTICO", min_length=2, max_length=30)


class InfluencerResponse(BaseModel):
    name: str
    handle: str
    category: str
    hype: int
    utility: int
    followers: int
    cliche: str
    verdict: str
    territory: str
    reality_level: str
    fact_id: int


@router.post("/ingest", response_model=StoreResponse)
async def ingest_influencer(
    req: InfluencerIngestRequest,
    auth: AuthResult = Depends(require_permission("write")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> StoreResponse:
    """Ingest/update a single influencer into the benchmark dataset using the Write-Path Contract."""
    try:
        content_payload = json.dumps(
            {
                "name": req.name,
                "handle": req.handle,
                "category": req.category,
                "hype": req.hype,
                "utility": req.utility,
                "followers": req.followers,
                "cliche": req.cliche,
                "verdict": req.verdict,
                "territory": req.territory,
                "reality_level": req.reality_level,
            }
        )

        fact_id = await engine.store(
            project="benchmark",
            content=content_payload,
            tenant_id=auth.tenant_id,
            fact_type="influencer",
            tags=["benchmark", req.category, req.territory.lower()],
            source="benchmark_api",
            meta={"hype": req.hype, "utility": req.utility, "reality_level": req.reality_level},
        )
        return StoreResponse(
            fact_id=fact_id, project="benchmark", message="Influencer ingested successfully"
        )
    except Exception as e:
        logger.exception("Failed to ingest influencer: %s", e)
        raise HTTPException(status_code=500, detail="Failed to ingest influencer") from None


@router.get("/list", response_model=list[InfluencerResponse])
async def list_influencers(
    limit: int = Query(100, ge=1, le=1000),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[InfluencerResponse]:
    """Retrieve all active benchmark influencers (public read, rate-limited and CORS protected)."""
    try:
        # Benchmark data is globally readable, we recall under the default scope
        facts = await engine.recall(project="benchmark", tenant_id="default", limit=limit)

        result: list[InfluencerResponse] = []
        for fact in facts:
            # We bypass private mapping protocols to read clean dict
            fact_dict = getattr(fact, "to_dict", lambda: None)()
            if not fact_dict or "content" not in fact_dict:
                continue

            try:
                data = json.loads(fact_dict["content"])
                result.append(
                    InfluencerResponse(
                        name=data["name"],
                        handle=data["handle"],
                        category=data["category"],
                        hype=int(data["hype"]),
                        utility=int(data["utility"]),
                        followers=int(data["followers"]),
                        cliche=data["cliche"],
                        verdict=data["verdict"],
                        territory=data.get("territory", "ES"),
                        reality_level=data.get(
                            "reality_level",
                            fact_dict.get("meta", {}).get("reality_level", "C4-SINTÉTICO"),
                        ),
                        fact_id=fact_dict["id"],
                    )
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return result
    except Exception as e:
        logger.exception("Failed to retrieve influencer list: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving benchmark"
        ) from None
