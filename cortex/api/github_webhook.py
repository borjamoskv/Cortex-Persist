from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhook", tags=["github"])

# Secret configured in the GitHub App
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "dev_secret").encode("utf-8")

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify that the webhook payload was actually sent by GitHub."""
    if not signature_header:
        return False
    hash_object = hmac.new(WEBHOOK_SECRET, msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

from cortex.llm.evaluator import SemanticRiskEvaluator

async def process_pull_request(payload: Dict[str, Any]):
    """Background task to process the PR risk scoring."""
    action = payload.get("action")
    if action not in ["opened", "synchronize", "reopened"]:
        return

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    
    pr_id = str(pr.get("number"))
    tenant_id = repo.get("full_name")
    
    logger.info(f"Processing PR {pr_id} for tenant {tenant_id}")
    
    # Extract structural metrics
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    changed_files = pr.get("changed_files", 0)
    
    churn = additions + deletions
    structural_entropy = min(1.0, churn / 1000.0) # Dummy proxy
    
    # Evaluate semantics
    evaluator = SemanticRiskEvaluator()
    decision = evaluator.evaluate_pr(
        intent=pr.get("title", "Unknown Intent"),
        diff="...simulated diff...",
        structural_entropy=structural_entropy
    )
    
    logger.info(f"PR {pr_id} evaluated. Structural Churn: {churn} lines. Decision: {decision['suggested_action']} (Risk: {decision['risk_level']})")

@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Ingests GitHub webhook events, verifies signatures, and routes to the Risk Pipeline.
    """
    signature = request.headers.get("x-hub-signature-256")
    body = await request.body()
    
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")
        
    event_type = request.headers.get("x-github-event")
    payload = await request.json()
    
    if event_type == "pull_request":
        background_tasks.add_task(process_pull_request, payload)
        return {"status": "accepted", "message": "PR queued for risk evaluation"}
        
    return {"status": "ignored", "message": f"Event {event_type} ignored"}
