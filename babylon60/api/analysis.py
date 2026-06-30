# [C5-REAL] Exergy-Maximized - SOTA BFT-Ready Analysis API
# Autoría: Borja Moskv (borjamoskv)
# Descargo: Exclusivo para el Teorema-Robinson-Moskv de CORTEX.

import os
import sqlite3
import time
import json
import math
from datetime import datetime, UTC
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

# API Versioning and Metadata
__version__ = "2.3.0"

JWT_SECRET = os.getenv("CORTEX_JWT_SECRET", "moskv-omega-strict-key-2026")
JWT_ALGORITHM = "HS256"
DB_PATH = os.path.expanduser("~/.babylon60/cortex.db")
MEMORY_PATH = os.path.expanduser("~/.agent/memory")
LOG_DIR = os.path.expanduser("~/.babylon60/logs")

# Thread Pool for non-blocking I/O
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(
    title="CORTEX Analysis Pipeline (MOSKV-1 OMEGA)",
    version=__version__,
    docs_url=None,
    description="Sovereign Endpoint for BFT-validated external AI audits. Created by Borja Moskv."
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

# Structured JSONL Audit Logger
def log_audit_event(method: str, path: str, ip: str, status: int, latency: float, user: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "api_audit.jsonl")
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "method": method,
        "path": path,
        "ip": ip,
        "status": status,
        "latency_ms": latency,
        "user": user
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[AUDIT LOG ERROR] {e}")

# Forensic Middleware
@app.middleware("http")
async def forensic_audit_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Exergy-Latency-Ms"] = f"{process_time:.2f}"
    
    # Retrieve user authorization from request headers safely
    user = "anonymous"
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user = payload.get("user", "sys_auditor")
        except Exception:
            user = "invalid_token"

    log_audit_event(
        method=request.method,
        path=request.url.path,
        ip=request.client.host if request.client else "unknown",
        status=response.status_code,
        latency=process_time,
        user=user
    )
    return response

def verify_strict_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="MISSING_BFT_AUTHORIZATION")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="INVALID_BFT_SCHEME")
        
        # Verify strict HS256 signature
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="BFT_TOKEN_EXPIRED")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"BFT_SIGNATURE_INVALID: {str(e)}")

def _query_db_worker(query: str) -> list[FactNode]:
    """Synchronous worker thread to query the WAL SQLite Database safely"""
    facts = []
    if not os.path.exists(DB_PATH):
        return facts

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        cursor = conn.cursor()

        tables = {
            "primitivas_de_colapso": ["id", "primitiva", "mecanismo_causal"],
            "invariantes_termodinamicas": ["id", "invariante", "lógica___principio", "implicación_operacional"],
            "antipatrones_estocasticos": ["id", "antipatrón", "disfunción_causal", "refactor_alternativa"],
            "redundancias_activas": ["id", "redundancia_c5", "función_topológica"],
            "vectores_adversariales": ["id", "vector_adversarial", "mecanismo_de_explotación"]
        }

        for table, cols in tables.items():
            # Check table existence to prevent crash if migration is pending
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                continue

            if query.lower() == "all":
                select_query = f"SELECT id, * FROM {table}"
                cursor.execute(select_query)
            else:
                # Sanitize and compile LIKE conditions safely
                conditions = " OR ".join([f"{col} LIKE ?" for col in cols])
                select_query = f"SELECT id, * FROM {table} WHERE {conditions}"
                params = [f"%{query}%"] * len(cols)
                cursor.execute(select_query, params)

            rows = cursor.fetchall()
            col_names = [description[0] for description in cursor.description]

            for row in rows:
                row_dict = dict(zip(col_names, row))
                entity_id = row_dict.get("id", "UNKNOWN")
                
                content_parts = []
                for k, v in row_dict.items():
                    if k != "id" and v:
                        content_parts.append(f"{k.replace('___', '/').replace('_', ' ').capitalize()}: {v}")
                
                content_str = " | ".join(content_parts)
                facts.append(FactNode(
                    id=entity_id,
                    level="C5-REAL",
                    content=content_str,
                    timestamp=datetime.now(UTC).isoformat()
                ))
    except Exception as e:
        print(f"[DB WORKER ERROR] {e}")
    finally:
        if conn:
            conn.close()
    return facts

def _read_memory_worker(query: str) -> list[FactNode]:
    """Synchronous worker thread to read cortex system memory"""
    ghosts_file = os.path.join(MEMORY_PATH, "ghosts.json")
    facts = []
    if os.path.exists(ghosts_file):
        try:
            with open(ghosts_file, encoding="utf-8") as f:
                data = json.load(f)
                for proj, ghost in data.items():
                    task = ghost.get("last_task", "")
                    if query.lower() in task.lower() or query.lower() == "all":
                        facts.append(FactNode(
                            id=f"GHOST-{proj.upper()}",
                            content=f"Project: {proj} | Task: {task} | Status: {ghost.get('status', 'active')}",
                            timestamp=ghost.get("timestamp", datetime.now(UTC).isoformat())
                        ))
        except Exception as e:
            print(f"[MEMORY WORKER ERROR] {e}")
    return facts

@app.get("/health")
def health_check():
    return {
        "status": "C5-REAL",
        "engine": "MOSKV-1 OMEGA",
        "timestamp": datetime.now(UTC).isoformat(),
        "entropy_leak": 0.0,
        "author": "Borja Moskv"
    }

@app.get("/facts", response_model=AuditResponse)
async def get_facts(
    request: Request,
    query: str = Query(..., min_length=2, description="BFT Extractor Query (use 'all' for full ledger)"),
    user: dict = Depends(verify_strict_token),
):
    """
    Exposes CORTEX-Persist C5-REAL crystallized memory using non-blocking ThreadPool offloading.
    Requires valid HS256 Bearer Token.
    """
    t0 = time.time()
    
    # Path traversal protection: block dots and slashes in query unless it is exact 'all'
    if query != "all" and (".." in query or "/" in query or "\\" in query):
        raise HTTPException(status_code=400, detail="Anergía Detectada: Query contiene caracteres prohibidos")

    # Run Database and Memory queries in separate threads concurrently to maximize exergy
    loop = request.app.state.loop if hasattr(request.app.state, "loop") else None
    import asyncio
    if not loop:
        loop = asyncio.get_running_loop()

    ontology_task = loop.run_in_executor(executor, _query_db_worker, query)
    memory_task = loop.run_in_executor(executor, _read_memory_worker, query)

    ontology_nodes, ghost_nodes = await asyncio.gather(ontology_task, memory_task)
    results = ontology_nodes + ghost_nodes
    
    return AuditResponse(
        query=query,
        nodes_yield=len(results),
        results=results,
        authorized_by=user.get("user", "sys_auditor"),
        exergy_latency_ms=(time.time() - t0) * 1000
    )

# Shannon Entropy Analyzer Endpoint
@app.get("/entropy")
def get_entropy_signature(payload: str = Query(..., min_length=2)):
    """Computes Shannon Entropy of target payloads before compilation ingestion."""
    if not payload:
        return {"entropy": 0.0, "classification": "EMPTY"}
    
    frequencies = {}
    for char in payload:
        frequencies[char] = frequencies.get(char, 0) + 1
    
    total = len(payload)
    entropy = 0.0
    for count in frequencies.values():
        p = count / total
        entropy -= p * (math.log2(p))
    
    return {
        "entropy": round(entropy, 4),
        "classification": "STRUCTURAL_NOIR" if entropy > 3.5 else "LOW_EXERGY"
    }

# Serve Custom themed Swagger
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Moskv Aesthetic UI",
        swagger_css_url="/static/swagger_theme.css",
    )
