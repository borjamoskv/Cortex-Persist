# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from cortex.api.deps import get_async_engine
from legacy_research.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine
from legacy_research.extensions.taas import JobExecutionResult, JobQuote, JobRequest, TaaSMarketplace

router = APIRouter(tags=["taas"])
logger = logging.getLogger("uvicorn.error")


_marketplace_instance: TaaSMarketplace | None = None


def get_taas_marketplace(engine: AsyncCortexEngine = Depends(get_async_engine)) -> TaaSMarketplace:
    global _marketplace_instance
    if _marketplace_instance is None:
        _marketplace_instance = TaaSMarketplace(engine)
    return _marketplace_instance


@router.post("/v1/taas/jobs/quote", response_model=JobQuote)
async def request_job_quote(
    req: JobRequest,
    auth: AuthResult = Depends(require_permission("write")),
    marketplace: TaaSMarketplace = Depends(get_taas_marketplace),
) -> JobQuote:
    """Request a quote and SLA for an agent execution job."""
    try:
        quote = await marketplace.quote_job(req)
        return quote
    except Exception as e:
        logger.error("Failed to generate TaaS quote: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate quote") from e


@router.post("/v1/taas/jobs/{job_id}/execute", response_model=JobExecutionResult)
async def execute_job(
    job_id: str,
    auth: AuthResult = Depends(require_permission("write")),
    marketplace: TaaSMarketplace = Depends(get_taas_marketplace),
) -> JobExecutionResult:
    """Execute a previously quoted job and receive proof of execution."""
    try:
        result = await marketplace.execute_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to execute TaaS job: %s", e)
        raise HTTPException(status_code=500, detail="Execution failed") from e


@router.get("/v1/taas/jobs/{job_id}/verify", response_model=dict)
async def verify_job_proof(
    job_id: str,
    proof: str,
    auth: AuthResult = Depends(require_permission("read")),
    marketplace: TaaSMarketplace = Depends(get_taas_marketplace),
) -> dict:
    """Verify cryptographic proof of execution for a job."""
    try:
        is_valid = await marketplace.verify_proof(job_id, proof)
        return {"job_id": job_id, "verified": is_valid}
    except Exception as e:
        logger.error("Failed to verify TaaS proof: %s", e)
        raise HTTPException(status_code=500, detail="Verification failed") from e
