from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import logging

setup_cortex_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CORTEX Code Governance Gateway",
    description="CI/CD Firewall and Policy Enforcement for AI Agents",
    version="1.0.0"
)

class PullRequestPayload(BaseModel):
    pr_id: str
    target_branch: str
    tenant_id: str
    additions: int
    deletions: int
    files_changed: int
    commits: int
    includes_tests: bool

@app.get("/health")
async def health_check():
    """Check resonance of the firewall."""
    return {"status": "resonant", "core": "CORTEX-MVP"}

from cortex.api.github_webhook import router as github_router

app.include_router(github_router)


@app.post("/api/v1/audit")
async def audit_pr(payload: PullRequestPayload):
    """
    Direct API endpoint for evaluating a PR payload against the Enterprise Policies.
    """
    # 1. Orchestrate the flow
    # identity = SovereignIdentity(...)
    # audit_result = gateway.evaluate_pull_request(identity, payload.pr_id, payload.dict())
    
    # Returning mock data until the internal wiring is fully ported
    return {
        "pr_id": payload.pr_id,
        "status": "EVALUATING",
        "risk_score": 0.0,
        "audit_proof": "pending_sha256"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
