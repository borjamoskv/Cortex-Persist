import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from medvi_rag.orchestrator.medvi_engine import MedviEngine

app = FastAPI(title="Medvi-RAG Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
app.mount("/dashboard", StaticFiles(directory=frontend_path, html=True), name="frontend")

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../medvi_poc.db'))
engine = MedviEngine(DB_PATH)

class IntentRequest(BaseModel):
    intent: str

@app.post("/api/intent")
def process_intent(req: IntentRequest):
    try:
        result = engine.process_intent(req.intent)
        if result:
            return result
        else:
            raise HTTPException(status_code=400, detail="Failed to process intent. Check logs.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import sqlite3

CORTEX_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../cortex.db'))

@app.get("/api/incubator")
def get_incubator_concepts():
    if not os.path.exists(CORTEX_DB_PATH):
        return {"concepts": []}
    try:
        with sqlite3.connect(CORTEX_DB_PATH) as conn:
            cursor = conn.execute("SELECT concept_hash, crystallized_data, timestamp FROM cortex_concepts ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            return {"concepts": [{"hash": r[0], "data": r[1], "timestamp": r[2]} for r in rows]}
    except Exception as e:
        return {"error": str(e), "concepts": []}
