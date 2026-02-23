"""CORTEX v5.0 — TIPS API Routes.

REST endpoints for the TIPS system.

Endpoints:
    GET /tips              → Random tip(s)
    GET /tips/categories   → List all categories
    GET /tips/category/{c} → Tips by category
    GET /tips/project/{p}  → Tips scoped to a project
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cortex.api_deps import get_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine
from cortex.tips import Tip, TipCategory, TipsEngine

__all__ = [
    "LANG_DESC",
    "get_tips",
    "get_tips_by_category",
    "get_tips_by_project",
    "list_categories",
]

router = APIRouter(prefix="/tips", tags=["tips"])

LANG_DESC = "Language code (en, es, eu)"

# Singleton tips engine (lazy init with engine)
_tips_engine: TipsEngine | None = None


def _get_tips_engine(engine: CortexEngine) -> TipsEngine:
    """Lazy-init the tips engine with the API's CORTEX engine."""
    global _tips_engine  # noqa: PLW0603
    if _tips_engine is None:
        _tips_engine = TipsEngine(engine, include_dynamic=True)
    return _tips_engine


def _tip_to_dict(tip: Tip) -> dict:
    """Serialize a Tip to JSON-friendly dict."""
    return {
        "id": tip.id,
        "content": tip.content,
        "category": tip.category.value,
        "lang": tip.lang,
        "source": tip.source,
        "project": tip.project,
        "relevance": tip.relevance,
        "formatted": tip.format(),
    }


# ─── Endpoints ───────────────────────────────────────────────────────


@router.get("")
async def get_tips(
    count: int = Query(1, ge=1, le=20, description="Number of tips to return"),
    lang: str = Query("en", description=LANG_DESC),
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get random contextual tips."""
    tips_engine = _get_tips_engine(engine)
    results = [tips_engine.random(lang=lang) for _ in range(count)]
    return {
        "tips": [_tip_to_dict(t) for t in results],
        "total_available": tips_engine.count,
        "lang": lang,
    }


@router.get("/categories")
async def list_categories(
    lang: str = Query("en", description=LANG_DESC),
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """List all tip categories with counts."""
    tips_engine = _get_tips_engine(engine)
    all_tips = tips_engine.all_tips(lang=lang)

    categories = {}
    for cat in TipCategory:
        cat_count = sum(1 for t in all_tips if t.category == cat)
        if cat_count > 0:
            categories[cat.value] = cat_count

    return {
        "categories": categories,
        "total": len(all_tips),
        "lang": lang,
    }


@router.get("/category/{category}")
async def get_tips_by_category(
    category: str,
    lang: str = Query("en", description=LANG_DESC),
    limit: int = Query(5, ge=1, le=50),
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get tips filtered by category."""
    tips_engine = _get_tips_engine(engine)
    results = tips_engine.for_category(category, lang=lang, limit=limit)
    return {
        "category": category,
        "tips": [_tip_to_dict(t) for t in results],
        "count": len(results),
        "lang": lang,
    }


@router.get("/project/{project}")
async def get_tips_by_project(
    project: str,
    lang: str = Query("en", description=LANG_DESC),
    limit: int = Query(3, ge=1, le=20),
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Get tips scoped to a specific project."""
    tips_engine = _get_tips_engine(engine)
    results = tips_engine.for_project(project, lang=lang, limit=limit)
    return {
        "project": project,
        "tips": [_tip_to_dict(t) for t in results],
        "count": len(results),
        "lang": lang,
    }
