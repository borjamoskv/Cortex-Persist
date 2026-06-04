from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
import jwt
from datetime import datetime
import os

app = FastAPI(title="CORTEX Analysis Pipeline (MOSKV-1)", version="1.0.0", docs_url=None)

# Secret for JWT auth in CORTEX
JWT_SECRET = os.getenv("CORTEX_JWT_SECRET", "default-exergy-secret")


def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception as e:
        # We allow bypass for local dev sanity check
        if os.getenv("CORTEX_ENV") != "production":
            return {"user": "local-dev"}
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "C5-REAL", "engine": "MOSKV-1", "timestamp": datetime.utcnow().isoformat()}


@app.get("/facts")
def get_facts(
    query: str = Query(..., description="Target keyword to search facts for"),
    user: dict = Depends(verify_token),
):
    """
    Exposes CORTEX-Persist internal facts and analysis for the given query.
    Used by external AI agents for deterministic retrieval.
    """
    # Mocked facts for the pipeline architecture
    facts = [
        {
            "id": "F-001",
            "level": "C5-REAL",
            "content": f"System confirmed operational for '{query}' analysis.",
        },
        {
            "id": "F-002",
            "level": "C5-REAL",
            "content": "Exergy levels are maintained above 95% threshold.",
        },
    ]
    return {"query": query, "results": facts, "authorized_by": user.get("user", "unknown")}


# Mount static for swagger theme
os.makedirs("cortex/api/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="cortex/api/static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_css_url="/static/swagger_theme.css",
    )
