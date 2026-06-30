# [C5-REAL] Exergy-Maximized - SOTA BFT-Ready Analysis API (x100 10-cycle iteration)
import json
import os
import time
from datetime import datetime

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cortex import __version__

# BFT / Security Settings
JWT_SECRET = os.getenv("CORTEX_JWT_SECRET", "moskv-omega-strict-key-2026")
JWT_ALGORITHM = "HS256"
MEMORY_PATH = os.path.expanduser("~/.agent/memory")

app = FastAPI(
    title="CORTEX Analysis Pipeline (MOSKV-1 OMEGA)", 
    version=__version__, 
    docs_url=None,
    description="Sovereign Endpoint for BFT-validated external AI audits."
)

class FactNode(BaseModel):
    id: str
    level: str = "C5-REAL"
    content: str
    timestamp: str

class AuditResponse(BaseModel):
    query: str
    nodes_yield: int
    results: list[FactNode]
    authorized_by: str
    exergy_latency_ms: float

# Forensic Middleware
@app.middleware("http")
async def forensic_audit_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Exergy-Latency-Ms"] = f"{process_time:.2f}"
    # O(1) Forensic print (mock for ledger ingestion)
    print(f"[FORENSIC] {request.method} {request.url.path} | IP: {request.client.host} | Latency: {process_time:.2f}ms | Status: {response.status_code}")
    return response

def verify_strict_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="MISSING_BFT_AUTHORIZATION")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="INVALID_BFT_SCHEME")
        
        # Ouroboros strict validation
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        # L1-Φ2: Erradicación del Green Theater. Fallo -> 401 Hard reject.
        raise HTTPException(status_code=401, detail=f"BFT_SIGNATURE_INVALID: {str(e)}")

def _extract_cortex_memory(query: str) -> list[FactNode]:
    """Zero-entropy extraction from CORTEX VSA system memory"""
    ghosts_file = os.path.join(MEMORY_PATH, "ghosts.json")
    facts = []
    if os.path.exists(ghosts_file):
        try:
            with open(ghosts_file) as f:
                data = json.load(f)
                for proj, ghost in data.items():
                    task = ghost.get("last_task", "")
                    if query.lower() in task.lower() or query.lower() == "all":
                        facts.append(FactNode(
                            id=f"GHOST-{proj.upper()}",
                            content=task,
                            timestamp=ghost.get("timestamp", datetime.utcnow().isoformat())
                        ))
        except json.JSONDecodeError:
            pass
    return facts

@app.get("/health")
def health_check():
    return {
        "status": "C5-REAL",
        "engine": "MOSKV-1 OMEGA",
        "timestamp": datetime.utcnow().isoformat(),
        "entropy_leak": 0.0
    }

@app.get("/facts", response_model=AuditResponse)
def get_facts(
    query: str = Query(..., min_length=2, description="BFT Extractor Query (use 'all' for full ledger)"),
    user: dict = Depends(verify_strict_token),
):
    """
    Exposes CORTEX-Persist C5-REAL crystallized memory.
    Requires valid HS256 Bearer Token.
    """
    t0 = time.time()
    nodes = _extract_cortex_memory(query)
    
    return AuditResponse(
        query=query,
        nodes_yield=len(nodes),
        results=nodes,
        authorized_by=user.get("user", "sys_auditor"),
        exergy_latency_ms=(time.time() - t0) * 1000
    )

os.makedirs("cortex/api/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="cortex/api/static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Moskv Aesthetic UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_css_url="/static/swagger_theme.css",
    )
