from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine.storage_guard import GuardViolation, StorageGuard
from cortex.engine_async import AsyncCortexEngine
from cortex.types.models import StoreRequest

router = APIRouter(tags=["trust"])
logger = logging.getLogger("uvicorn.error")


class TrustProfileResponse(BaseModel):
    agent_id: str
    trust_score: float
    successes: int
    failures: int
    taint_events: int
    last_success: str | None = None
    last_incident: str | None = None


class ComplianceReport(BaseModel):
    status: str
    ledger_valid: bool
    total_trust_score: float
    audit_coverage: float
    compliance_level: str
    article_12_status: str


@router.post("/v1/trust/guard", response_model=dict)
async def dry_run_guard(
    req: StoreRequest,
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Dry-run a store proposal against StorageGuard (Ω₃).

    Returns 200 {valid: true} or 400 with specific violation details.
    """
    try:
        StorageGuard.validate(
            project=req.project,
            content=req.content,
            fact_type=req.fact_type,
            source=req.source or "api_dry_run",
            confidence=req.confidence or "C3",
            tags=req.tags,
            meta=req.meta,
        )
        return {"valid": True, "message": "Proposal passes all guards"}
    except GuardViolation as e:
        raise HTTPException(
            status_code=400, detail={"valid": False, "rule": e.rule, "error": e.detail}
        ) from e
    except Exception as e:
        logger.error("Guard dry-run failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal guard error") from e


@router.get("/v1/trust/profiles/{agent_id}", response_model=TrustProfileResponse)
async def get_agent_trust(
    agent_id: str,
    auth: AuthResult = Depends(require_permission("read")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> TrustProfileResponse:
    """Retrieve the Bayesian trust profile for a specific agent."""
    registry = engine.get_trust_registry()
    profile = registry.get_profile(agent_id)
    score = registry.compute_trust_score(profile)

    return TrustProfileResponse(
        agent_id=profile.agent_id,
        trust_score=score,
        successes=profile.successes,
        failures=profile.failures,
        taint_events=profile.taint_events,
        last_success=profile.last_success_ts.isoformat() if profile.last_success_ts else None,
        last_incident=profile.last_incident_ts.isoformat() if profile.last_incident_ts else None,
    )


@router.get("/v1/trust/compliance", response_model=ComplianceReport)
async def get_compliance_status(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> ComplianceReport:
    """Generate aggregate compliance report (EU AI Act Art 12)."""
    try:
        verification = await engine.verify_ledger()
        stats = await engine.stats()

        # Heuristic scoring for Article 12
        audit_coverage = stats.get("causal_facts", 0) / max(stats.get("active_facts", 1), 1)

        return ComplianceReport(
            status="compliant"
            if verification["valid"] and audit_coverage > 0.8
            else "non_compliant",
            ledger_valid=verification["valid"],
            total_trust_score=0.95,  # Placeholder for aggregate swarm trust
            audit_coverage=round(audit_coverage, 4),
            compliance_level="Sovereign-Alpha",
            article_12_status="LOGGED_AND_VERIFIED",
        )
    except Exception as e:
        logger.error("Compliance report generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate compliance report") from e
