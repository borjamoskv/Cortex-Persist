from fastapi import FastAPI, HTTPException, Security, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
import os
import subprocess
import shlex
from pydantic import BaseModel

app = FastAPI(
    title="MOSKV-1 APEX Analysis Node",
    description="Vector de acceso para IA externas. Exposición de memoria, invariantes físicas y estado topológico del clúster.",
    version="5.0.0",
    docs_url=None
)

security = HTTPBearer()
EXPECTED_TOKEN = os.environ.get("CORTEX_ANALYSIS_TOKEN", "c5-real-omega-key")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != EXPECTED_TOKEN:
        raise HTTPException(status_code=403, detail="Anergía Detectada: Token Inválido")
    return credentials.credentials

class ScanRequest(BaseModel):
    target_path: str

class ScanResponse(BaseModel):
    untracked_files: int
    broken_symlinks: int
    massive_nodes: int
    status: str

# Create static directory if not exists
os.makedirs("cortex/api/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="cortex/api/static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_css_url="/static/swagger_theme.css"
    )

@app.get("/health")
async def health_check():
    return {
        "status": "C5-REAL",
        "exergy_level": "OPTIMAL",
        "entropy": 0.0,
        "mode": "Ultra-Think Ready"
    }

@app.get("/invariants")
async def get_invariants(token: str = Depends(verify_token)):
    inv_path = os.path.expanduser("~/30_CORTEX/docs/epistemology/100_invariantes_fisicas.md")
    if os.path.exists(inv_path):
        with open(inv_path, "r") as f:
            return {"source": "100_invariantes_fisicas.md", "content": f.read()}
    raise HTTPException(status_code=404, detail="Invariantes no forjadas en disco")

@app.post("/scan/topology", response_model=ScanResponse)
async def scan_topology(req: ScanRequest, token: str = Depends(verify_token)):
    """Ejecuta un barrido topológico sobre el path dado."""
    target = os.path.expanduser(req.target_path)
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Target path no existe")
    
    try:
        quoted_target = shlex.quote(target)
        untracked = subprocess.check_output(f"git -C {quoted_target} ls-files --others --exclude-standard | wc -l", shell=True)
        broken = subprocess.check_output(f"find {quoted_target} -type l ! -exec test -e {{}} \\; -print | wc -l", shell=True)
        massive = subprocess.check_output(f"find {quoted_target} -type f -size +50M -not -path '*/\\.*' | wc -l", shell=True)
        
        return ScanResponse(
            untracked_files=int(untracked.strip()),
            broken_symlinks=int(broken.strip()),
            massive_nodes=int(massive.strip()),
            status="WARNING" if int(untracked)>0 or int(broken)>0 else "CLEAN"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
