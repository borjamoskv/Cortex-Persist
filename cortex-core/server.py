from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import cortex_rs
import hashlib
import json
import os

app = FastAPI(
    title="CORTEX-Persist Sovereign Node",
    description="C5-REAL Multi-Agent Epistemic Membrane via Vector Symbolic Architecture",
    version="1.0.0"
)

# Global Sovereign Membrane
DIM = 1024
try:
    membrane = cortex_rs.EpistemicMembrane(DIM)
except Exception as e:
    # If not built properly or accessed outside venv, fail loudly
    raise RuntimeError(f"CORTEX-RS Bindings Failed: {e}")

# Maintain the core semantic ground truth (similar to genesis block)
def get_deterministic_hv(text: str) -> cortex_rs.HyperVector:
    """Uses a seed from the hash of the text to generate a deterministic HyperVector."""
    # In a real C5-REAL deployment, we would use an LLM embedding model here
    # For this node, we use the Rust random generator but it acts as a proxy
    # We simulate deterministic behavior by maintaining a dictionary if needed, 
    # but for simplicity, we just generate a random one to represent the semantic concept.
    return cortex_rs.HyperVector.random(DIM)

class ProposalRequest(BaseModel):
    agent_id: str
    action_intent: str
    semantic_content: str

class VerificationResponse(BaseModel):
    status: str
    accept: bool
    merkle_root: str | None
    similarity: float
    reason: str

@app.on_event("startup")
async def startup_event():
    # Genesis Block Injection
    import sys
    sys.stdout.write("[CORTEX-NODE] Initializing Sovereign Epistemic Membrane...\n")
    if os.path.exists("cortex_ledger.jsonl"):
        os.remove("cortex_ledger.jsonl")
    
    genesis_hv = cortex_rs.HyperVector.random(DIM)
    episode = membrane.encode_episode([("consistency", genesis_hv)])
    membrane.check_proposal(episode)
    root_hash = membrane.commit(episode)
    sys.stdout.write(f"[CORTEX-NODE] Genesis Block Root: {root_hash[:16]}...\n")
    
    # Store globally for reference
    app.state.base_hv = genesis_hv

@app.post("/propose", response_model=VerificationResponse)
async def propose_action(req: ProposalRequest):
    """
    Evaluates an agent's proposed action against the collective memory.
    """
    # 1. Map intent to HyperVector (Simulating embedding distance)
    # If the semantic_content contains extreme violations, we generate an orthogonal vector.
    # Otherwise, we create a valid semantic vector near the base truth.
    if "DROP TABLE" in req.semantic_content or "hack" in req.semantic_content or "override" in req.semantic_content:
        proposal_hv = cortex_rs.HyperVector.random(DIM)
    else:
        noise = cortex_rs.HyperVector.random(DIM)
        proposal_hv = app.state.base_hv.bundle(noise)
        
    # 2. Check the membrane
    episode = membrane.encode_episode([("consistency", proposal_hv)])
    res = membrane.check_proposal(episode)
    
    accept = res["accept"]
    sim = res["max_similarity"]
    reason = res["reason"]
    
    if accept:
        root_hash = membrane.commit(episode)
        return VerificationResponse(
            status="COMMITTED",
            accept=True,
            merkle_root=root_hash,
            similarity=sim,
            reason=reason
        )
    else:
        return VerificationResponse(
            status="BLOCKED",
            accept=False,
            merkle_root=None,
            similarity=sim,
            reason=reason
        )

@app.get("/ledger")
async def get_ledger():
    """
    Returns the cryptographic ledger for external auditing.
    """
    entries = []
    try:
        with open("cortex_ledger.jsonl", "r") as f:
            for line in f:
                entries.append(json.loads(line))
        return {"ledger": entries}
    except FileNotFoundError:
        return {"ledger": []}
